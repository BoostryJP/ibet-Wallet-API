"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import os
import sys
import time
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3.exceptions import ABIEventFunctionNotFound

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app import config
from app.contracts import Contract
from app.errors import ServiceUnavailable
from app.model.db import IDXTokenListBlockNumber, IDXTokenListItem
from app.utils.web3_utils import Web3Wrapper

process_name = "INDEXER-TOKEN-LIST"
LOG = log.get_logger(process_name=process_name)

web3 = Web3Wrapper()
db_engine = create_engine(config.DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing TokenList events"""

    def __init__(self):
        self.token_list_contract = Contract.get_contract(
            contract_name="TokenList", address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )
        self.available_token_template_list = []
        if config.BOND_TOKEN_ENABLED:
            self.available_token_template_list.append("IbetStraightBond")
        if config.SHARE_TOKEN_ENABLED:
            self.available_token_template_list.append("IbetShare")
        if config.MEMBERSHIP_TOKEN_ENABLED:
            self.available_token_template_list.append("IbetMembership")
        if config.COUPON_TOKEN_ENABLED:
            self.available_token_template_list.append("IbetCoupon")

    @staticmethod
    def __get_db_session():
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def process(self):
        local_session = self.__get_db_session()
        try:
            latest_block = web3.eth.block_number
            _from_block = (
                self.__get_idx_token_list_block_number(
                    db_session=local_session,
                    contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
                )
                + 1
            )
            _to_block = 999999 + _from_block
            if latest_block > _to_block:
                while _to_block < latest_block:
                    self.__sync_all(
                        db_session=local_session,
                        block_from=_from_block,
                        block_to=_to_block,
                    )
                    _to_block += 1000000
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=latest_block,
                )
            else:
                if _from_block > latest_block:
                    return
                self.__sync_all(
                    db_session=local_session,
                    block_from=_from_block,
                    block_to=latest_block,
                )
            self.__set_idx_token_list_block_number(
                db_session=local_session,
                contract_address=config.TOKEN_LIST_CONTRACT_ADDRESS,
                block_number=latest_block,
            )
            local_session.commit()
        except Exception as e:
            local_session.rollback()
            raise
        finally:
            local_session.close()
        LOG.info("Sync job has been completed")

    def __sync_all(self, db_session: Session, block_from: int, block_to: int):
        LOG.info("Syncing from={}, to={}".format(block_from, block_to))
        self.__sync_register(db_session, block_from, block_to)

    def __sync_register(self, db_session: Session, block_from: int, block_to: int):
        """Sync Register Events

        :param db_session: ORM session
        :param block_from: From block
        :param block_to: To block
        :return: None
        """
        try:
            events = self.token_list_contract.events.Register.getLogs(
                fromBlock=block_from, toBlock=block_to
            )
        except ABIEventFunctionNotFound:
            events = []
        try:
            for _event in events:
                token_address = _event["args"].get("token_address")
                token_template = _event["args"].get("token_template")
                owner_address = _event["args"].get("owner_address")
                self.__sink_on_token_info(
                    db_session=db_session,
                    token_address=token_address,
                    token_template=token_template,
                    owner_address=owner_address,
                )
        except Exception as e:
            raise e

    def __sink_on_token_info(
        self,
        db_session: Session,
        token_address: str,
        token_template: str,
        owner_address: str,
    ):
        """Update Token Info item in DB

        :param db_session: ORM session
        :param token_address: token address
        :param token_template: token template
        :param owner_address: owner address
        :return: None
        """
        if token_template not in self.available_token_template_list:
            return

        idx_token_list: Optional[IDXTokenListItem] = (
            db_session.query(IDXTokenListItem)
            .filter(IDXTokenListItem.token_address == token_address)
            .first()
        )
        if idx_token_list is not None:
            idx_token_list.token_template = token_template
            idx_token_list.owner_address = owner_address
            db_session.merge(idx_token_list)
        else:
            idx_token_list = IDXTokenListItem()
            idx_token_list.token_address = token_address
            idx_token_list.token_template = token_template
            idx_token_list.owner_address = owner_address
            db_session.add(idx_token_list)

    @staticmethod
    def __get_idx_token_list_block_number(db_session: Session, contract_address: str):
        """Get token list index for Share"""
        _idx_token_list_block_number = (
            db_session.query(IDXTokenListBlockNumber)
            .filter(IDXTokenListBlockNumber.contract_address == contract_address)
            .first()
        )
        if _idx_token_list_block_number is None:
            return -1
        else:
            return _idx_token_list_block_number.latest_block_number

    @staticmethod
    def __set_idx_token_list_block_number(
        db_session: Session, contract_address: str, block_number: int
    ):
        """Get token list index for Share"""
        _idx_token_list_block_number = (
            db_session.query(IDXTokenListBlockNumber)
            .filter(IDXTokenListBlockNumber.contract_address == contract_address)
            .first()
        )
        if _idx_token_list_block_number is None:
            _idx_token_list_block_number = IDXTokenListBlockNumber()
        _idx_token_list_block_number.latest_block_number = block_number
        _idx_token_list_block_number.contract_address = contract_address
        db_session.merge(_idx_token_list_block_number)


def main():
    LOG.info("Service started successfully")
    processor = Processor()

    while True:
        try:
            processor.process()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:
            LOG.exception("An exception occurred during event synchronization")

        time.sleep(5)


if __name__ == "__main__":
    main()
