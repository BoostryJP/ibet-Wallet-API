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

import logging
from typing import Sequence
from unittest import mock
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import RPCEndpoint

from app import config
from app.errors import ServiceUnavailable
from app.model.db import IDXBlockData, IDXBlockDataBlockNumber, IDXTxData
from batch.indexer_Block_Tx_Data import LOG, Processor
from tests.account_config import eth_account
from tests.utils import IbetStandardTokenUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


def _transactions_len(block_data: IDXBlockData) -> int:
    transactions = block_data.transactions
    assert transactions is not None
    return len(transactions)


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield caplog
    LOG.propagate = False
    LOG.setLevel(default_log_level)


@pytest.fixture(scope="function")
def processor() -> Processor:
    processor = Processor()
    return processor


@pytest.mark.asyncio
class TestProcessor:
    @staticmethod
    def set_block_number(session: Session, block_number: int):
        indexed_block_number = IDXBlockDataBlockNumber()
        indexed_block_number.chain_id = config.WEB3_CHAINID
        indexed_block_number.latest_block_number = block_number
        session.add(indexed_block_number)
        session.commit()

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # Skip process: from_block > latest_block
    async def test_normal_1(
        self, processor: Processor, session: Session, caplog: pytest.LogCaptureFixture
    ):
        before_block_number = web3.eth.block_number
        self.set_block_number(session, before_block_number)

        # Execute batch processing
        await processor.process()

        # Assertion
        indexed_block = session.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == config.WEB3_CHAINID)
            .limit(1)
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == before_block_number

        block_data: Sequence[IDXBlockData] = session.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 0

        tx_data: Sequence[IDXTxData] = session.scalars(
            select(IDXTxData).order_by(IDXTxData.block_number)
        ).all()
        assert len(tx_data) == 0

        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "Skip process: from_block > latest_block")
        )

    # Normal_2
    # BlockData: Empty block is generated
    async def test_normal_2(
        self, processor: Processor, session: Session, caplog: pytest.LogCaptureFixture
    ):
        before_block_number = web3.eth.block_number
        self.set_block_number(session, before_block_number)

        # Generate empty block
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Execute batch processing
        await processor.process()
        after_block_number = web3.eth.block_number

        # Assertion: Data
        indexed_block = session.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == config.WEB3_CHAINID)
            .limit(1)
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == after_block_number

        block_data: Sequence[IDXBlockData] = session.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 2
        assert block_data[0].number == before_block_number + 1
        assert block_data[1].number == before_block_number + 2

        tx_data: Sequence[IDXTxData] = session.scalars(
            select(IDXTxData).order_by(IDXTxData.block_number)
        ).all()
        assert len(tx_data) == 0

        # Assertion: Log
        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                f"Syncing from={before_block_number + 1}, to={after_block_number}",
            )
        )
        assert 1 == caplog.record_tuples.count(
            (LOG.name, logging.INFO, "Sync job has been completed")
        )

    # Normal_3_1
    # TxData: Contract deployment
    async def test_normal_3_1(
        self, processor: Processor, session: Session, caplog: pytest.LogCaptureFixture
    ):
        deployer = eth_account["issuer"]["account_address"]

        before_block_number = web3.eth.block_number
        self.set_block_number(session, before_block_number)

        # Deploy contract
        IbetStandardTokenUtils.issue(
            tx_from=deployer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": config.ZERO_ADDRESS,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )

        # Execute batch processing
        await processor.process()
        after_block_number = web3.eth.block_number

        # Assertion
        indexed_block = session.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == config.WEB3_CHAINID)
            .limit(1)
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == after_block_number

        block_data: Sequence[IDXBlockData] = session.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 1
        assert block_data[0].number == before_block_number + 1
        assert _transactions_len(block_data[0]) == 1

        tx_data: Sequence[IDXTxData] = session.scalars(
            select(IDXTxData).order_by(IDXTxData.block_number)
        ).all()
        assert len(tx_data) == 1
        assert tx_data[0].block_hash == block_data[0].hash
        assert tx_data[0].block_number == before_block_number + 1
        assert tx_data[0].transaction_index == 0
        assert tx_data[0].from_address == deployer
        assert tx_data[0].to_address is None

    # Normal_3_2
    # TxData: Transaction
    async def test_normal_3_2(
        self, processor: Processor, session: Session, caplog: pytest.LogCaptureFixture
    ):
        deployer = eth_account["issuer"]["account_address"]
        to_address = eth_account["user1"]["account_address"]

        before_block_number = web3.eth.block_number
        self.set_block_number(session, before_block_number)

        # Deploy contract -> Transfer
        token_contract = IbetStandardTokenUtils.issue(
            tx_from=deployer,
            args={
                "name": "test_token",
                "symbol": "TEST",
                "totalSupply": 1000,
                "tradableExchange": config.ZERO_ADDRESS,
                "contactInformation": "test_contact_info",
                "privacyPolicy": "test_privacy_policy",
            },
        )
        tx_hash = token_contract.functions.transfer(to_address, 1).transact(
            {"from": deployer}
        )

        # Execute batch processing
        await processor.process()
        after_block_number = web3.eth.block_number

        # Assertion
        indexed_block = session.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == config.WEB3_CHAINID)
            .limit(1)
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == after_block_number

        block_data: Sequence[IDXBlockData] = session.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 2

        assert block_data[0].number == before_block_number + 1
        assert _transactions_len(block_data[0]) == 1

        assert block_data[1].number == before_block_number + 2
        assert _transactions_len(block_data[1]) == 1

        tx_data: Sequence[IDXTxData] = session.scalars(
            select(IDXTxData).order_by(IDXTxData.block_number)
        ).all()
        assert len(tx_data) == 2

        assert tx_data[0].block_hash == block_data[0].hash
        assert tx_data[0].block_number == before_block_number + 1
        assert tx_data[0].transaction_index == 0
        assert tx_data[0].from_address == deployer
        assert tx_data[0].to_address is None

        assert tx_data[1].hash == tx_hash.to_0x_hex()
        assert tx_data[1].block_hash == block_data[1].hash
        assert tx_data[1].block_number == before_block_number + 2
        assert tx_data[1].transaction_index == 0
        assert tx_data[1].from_address == deployer
        assert tx_data[1].to_address == token_contract.address

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1: ServiceUnavailable
    async def test_error_1(self, processor: Processor, session: Session):
        before_block_number = web3.eth.block_number
        self.set_block_number(session, before_block_number)

        # Execute batch processing
        with (
            mock.patch(
                "web3.AsyncWeb3.AsyncHTTPProvider.make_request",
                MagicMock(side_effect=ServiceUnavailable()),
            ),
            pytest.raises(ServiceUnavailable),
        ):
            await processor.process()

        # Assertion
        indexed_block = session.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == config.WEB3_CHAINID)
            .limit(1)
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == before_block_number

        block_data: Sequence[IDXBlockData] = session.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 0

        tx_data: Sequence[IDXTxData] = session.scalars(
            select(IDXTxData).order_by(IDXTxData.block_number)
        ).all()
        assert len(tx_data) == 0

    # Error_2: SQLAlchemyError
    async def test_error_2(self, processor: Processor, session: Session):
        before_block_number = web3.eth.block_number
        self.set_block_number(session, before_block_number)

        # Generate empty block
        web3.provider.make_request(RPCEndpoint("evm_mine"), [])

        # Execute batch processing
        with (
            mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),
            pytest.raises(SQLAlchemyError),
        ):
            await processor.process()

        # Assertion
        indexed_block = session.scalars(
            select(IDXBlockDataBlockNumber)
            .where(IDXBlockDataBlockNumber.chain_id == config.WEB3_CHAINID)
            .limit(1)
        ).first()
        assert indexed_block is not None
        assert indexed_block.latest_block_number == before_block_number

        block_data: Sequence[IDXBlockData] = session.scalars(
            select(IDXBlockData).order_by(IDXBlockData.number)
        ).all()
        assert len(block_data) == 0

        tx_data: Sequence[IDXTxData] = session.scalars(
            select(IDXTxData).order_by(IDXTxData.block_number)
        ).all()
        assert len(tx_data) == 0
