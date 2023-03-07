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
from dataclasses import dataclass
from typing import List, Type

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import ObjectDeletedError

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app import config
from app.errors import ServiceUnavailable
from app.model.blockchain import (
    BondToken,
    CouponToken,
    MembershipToken,
    ShareToken,
    TokenClassTypes,
)
from app.model.db import IDXBondToken as BondTokenModel
from app.model.db import IDXCouponToken as CouponTokenModel
from app.model.db import IDXMembershipToken as MembershipTokenModel
from app.model.db import IDXShareToken as ShareTokenModel
from app.model.db import IDXTokenInstance, Listing

process_name = "INDEXER-TOKEN-DETAIL-SHORT-TERM"
LOG = log.get_logger(process_name=process_name)

db_engine = create_engine(config.DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing token detail attributes for short term"""

    @dataclass
    class TargetTokenType:
        template: str
        token_class: Type[TokenClassTypes]
        token_model: Type[IDXTokenInstance]

    target_token_types: List[TargetTokenType]
    SEC_PER_RECORD: float = config.TOKEN_SHORT_TERM_FETCH_INTERVAL_MSEC / 1000

    def __init__(self):
        self.target_token_types = []
        if config.BOND_TOKEN_ENABLED:
            self.target_token_types.append(
                self.TargetTokenType(
                    template="IbetStraightBond",
                    token_class=BondToken,
                    token_model=BondTokenModel,
                )
            )
        if config.SHARE_TOKEN_ENABLED:
            self.target_token_types.append(
                self.TargetTokenType(
                    template="IbetShare",
                    token_class=ShareToken,
                    token_model=ShareTokenModel,
                )
            )
        if config.MEMBERSHIP_TOKEN_ENABLED:
            self.target_token_types.append(
                self.TargetTokenType(
                    template="IbetMembership",
                    token_class=MembershipToken,
                    token_model=MembershipTokenModel,
                )
            )
        if config.COUPON_TOKEN_ENABLED:
            self.target_token_types.append(
                self.TargetTokenType(
                    template="IbetCoupon",
                    token_class=CouponToken,
                    token_model=CouponTokenModel,
                )
            )

    @staticmethod
    def __get_db_session() -> Session:
        return Session(autocommit=False, autoflush=True, bind=db_engine)

    def process(self):
        LOG.info("Syncing token details")
        start_time = time.time()
        local_session = self.__get_db_session()
        try:
            self.__sync(local_session)
        except Exception:
            local_session.rollback()
            local_session.close()
            raise
        finally:
            local_session.close()
        elapsed_time = time.time() - start_time
        LOG.info(f"Sync job has been completed in {elapsed_time:.3f} sec")

    def __sync(self, local_session: Session):
        for token_type in self.target_token_types:
            available_tokens = (
                local_session.query(token_type.token_model)
                .join(
                    Listing,
                    token_type.token_model.token_address == Listing.token_address,
                )
                .filter(Listing.is_public == True)
                .all()
            )

            for available_token in available_tokens:
                try:
                    start_time = time.time()
                    token = token_type.token_class.from_model(available_token)
                    token.fetch_expiry_short()
                    token_model = token.to_model()
                    local_session.merge(token_model)
                    local_session.commit()

                    # Keep request interval constant to avoid throwing many request to JSON-RPC
                    elapsed_time = time.time() - start_time
                    time.sleep(max(self.SEC_PER_RECORD - elapsed_time, 0))
                except ObjectDeletedError:
                    LOG.warning(
                        "The record may have been deleted in another session during the update"
                    )


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()

        try:
            processor.process()
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:  # Unexpected errors
            LOG.exception("An exception occurred during event synchronization")

        elapsed_time = time.time() - start_time
        time_to_sleep = max(
            config.TOKEN_SHORT_TERM_CACHE_REFRESH_INTERVAL - elapsed_time, 0
        )
        if time_to_sleep == 0:
            LOG.debug("Processing is delayed")
        time.sleep(time_to_sleep)


if __name__ == "__main__":
    main()
