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

import json
import logging
from typing import Sequence
from unittest import mock
from unittest.mock import MagicMock

import pytest
import requests
from eth_utils.address import to_checksum_address
from sqlalchemy import select

from app.model.db import TokenList
from batch.indexer_PublicInfo_TokenList import LOG, Processor


@pytest.fixture(scope="function")
def processor(session):
    return Processor()


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    _log = logging.getLogger("ibet_wallet_batch")
    default_log_level = _log.level
    _log.setLevel(logging.INFO)
    _log.propagate = True
    yield caplog
    _log.propagate = False
    _log.setLevel(default_log_level)


class MockResponse:
    def __init__(self, data: object, status_code: int = 200):
        self.data = data
        self.status_code = status_code

    def json(self) -> object:
        return self.data


@pytest.mark.asyncio
class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    token_address_1 = "0xE883a6F441Ad5682D37Df31d34fC012bcb07A741"
    token_address_2 = "0xE883A6f441AD5682D37df31d34FC012bcB07a742"
    token_address_3 = "0xe883a6f441AD5682d37dF31D34fc012bCB07A743"
    token_address_4 = "0xe883A6F441AD5682d37dF31d34fc012BcB07a744"
    token_address_5 = "0xe883A6F441AD5682d37df31D34fc012BcB07A745"
    issuer_address_1 = "0xe883a6f441ad5682d37df31d34fc012bcb07a746"

    # <Normal_1>
    # 0 record
    @mock.patch("requests.Session.get")
    async def test_normal_1(self, mock_get, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([])]

        # Run target process
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 0

    # <Normal_2>
    # 1 record
    @mock.patch("requests.Session.get")
    async def test_normal_2(self, mock_get, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                ]
            )
        ]

        # Run target process
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1
        assert _token_list[0].token_address == self.token_address_4  # checksum address
        assert _token_list[0].token_template == "ibetShare"
        assert _token_list[0].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[0].product_type == 1

    # <Normal_3>
    # 2 record
    @mock.patch("requests.Session.get")
    async def test_normal_3(self, mock_get, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                    {
                        "token_address": self.token_address_5,
                        "token_template": "ibetBond",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                ]
            )
        ]

        # Run target process
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 2
        assert _token_list[0].token_address == self.token_address_4  # checksum address
        assert _token_list[0].token_template == "ibetShare"
        assert _token_list[0].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[0].product_type == 1
        assert _token_list[1].token_address == self.token_address_5  # checksum address
        assert _token_list[1].token_template == "ibetBond"
        assert _token_list[1].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[1].product_type == 1

    # <Normal_issuer_address>
    # issuer_address is stored as checksum address
    @mock.patch("requests.Session.get")
    async def test_normal_issuer_address(self, mock_get, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                        "issuer_address": self.issuer_address_1,
                    },
                ]
            )
        ]

        # Run target process
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1
        assert _token_list[0].token_address == self.token_address_4  # checksum address
        assert _token_list[0].token_template == "ibetShare"
        assert _token_list[0].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[0].product_type == 1
        assert _token_list[0].issuer_address == to_checksum_address(
            self.issuer_address_1
        )

    # <Normal_4_1>
    # There are no differences from last time
    # -> Skip this cycle
    @mock.patch("requests.Session.get")
    async def test_normal_4_1(self, mock_get, processor, async_session, caplog):
        # Run target process: 1st time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                    {
                        "token_address": self.token_address_5,
                        "token_template": "ibetBond",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                ]
            )
        ]
        processor.process()

        # Run target process: 2nd time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                    {
                        "token_address": self.token_address_5,
                        "token_template": "ibetBond",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                ]
            )
        ]
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 2
        assert _token_list[0].token_address == self.token_address_4  # checksum address
        assert _token_list[0].token_template == "ibetShare"
        assert _token_list[0].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[0].product_type == 1
        assert _token_list[1].token_address == self.token_address_5  # checksum address
        assert _token_list[1].token_template == "ibetBond"
        assert _token_list[1].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[1].product_type == 1

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                "Skip: There are no differences from the previous cycle",
            )
        )

    # <Normal_4_2>
    # There are differences from the previous cycle
    @mock.patch("requests.Session.get")
    async def test_normal_4_2(self, mock_get, processor, async_session, caplog):
        # Run target process: 1st time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                    {
                        "token_address": self.token_address_5,
                        "token_template": "ibetBond",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                ]
            )
        ]
        processor.process()

        # Run target process: 2nd time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                ]
            )
        ]
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1
        assert _token_list[0].token_address == self.token_address_4  # checksum address
        assert _token_list[0].token_template == "ibetShare"
        assert _token_list[0].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[0].product_type == 1

        assert 0 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                "Skip: There are no differences from the previous cycle",
            )
        )

    ###########################################################################
    # Error Case
    ###########################################################################

    # <Error_1_1>
    # API error: ConnectionError
    @mock.patch(
        "requests.Session.get",
        MagicMock(side_effect=requests.exceptions.ConnectionError),
    )
    async def test_error_1_1(self, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        await async_session.commit()

        # Run target process
        processor.process()

        # Assertion
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1

    # <Error_1_2>
    # API error: Not succeed request
    @mock.patch("requests.Session.get")
    async def test_error_1_2(self, mock_get, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([], 400)]

        # Run target process
        processor.process()

        # Assertion
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1

    # <Error_1_3>
    # API error: JSONDecodeError
    @mock.patch(
        "requests.Session.get",
        MagicMock(side_effect=json.decoder.JSONDecodeError),
    )
    async def test_error_1_3(self, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        await async_session.commit()

        # Run target process
        processor.process()

        # Assertion
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1

    # <Error_2>
    # Invalid type error
    # -> Skip processing
    @mock.patch("requests.Session.get")
    @pytest.mark.parametrize(
        "invalid_record",
        [
            {
                "token_address": "invalid_address",
                "token_template": "ibetShare",
                "key_manager": ["0000000000000", "1111111111111"],
                "product_type": 1,
            },  # invalid token_address
            {
                "token_address": token_address_5,
                "token_template": 123,
                "key_manager": ["0000000000000", "1111111111111"],
                "product_type": 1,
            },  # invalid token_template
            {
                "token_address": token_address_5,
                "token_template": 123,
                "key_manager": "0000000000000",
                "product_type": 1,
            },  # invalid key_manager
            {
                "token_address": token_address_5,
                "token_template": 123,
                "key_manager": "0000000000000",
                "product_type": 1,
            },  # invalid product_type
            {
                "token_template": "ibetShare",
                "key_manager": ["0000000000000", "1111111111111"],
                "product_type": 1,
            },  # token_address missing
            {
                "token_address": token_address_5,
                "key_manager": ["0000000000000", "1111111111111"],
                "product_type": 1,
            },  # token_template missing
            {
                "token_address": token_address_5,
                "token_template": 123,
                "product_type": 1,
            },  # key_manager missing
            {
                "token_address": token_address_5,
                "token_template": 123,
                "key_manager": "0000000000000",
            },  # product_type missing
        ],
    )
    async def test_error_2(self, mock_get, processor, async_session, invalid_record):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                    invalid_record,
                ]
            )
        ]

        # Run target process
        processor.process()

        # Assertion
        await async_session.rollback()
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1
        assert _token_list[0].token_address == self.token_address_4  # checksum address
        assert _token_list[0].token_template == "ibetShare"
        assert _token_list[0].key_manager == ["0000000000000", "1111111111111"]
        assert _token_list[0].product_type == 1

    # <Error_3>
    # Other error
    @mock.patch("requests.Session.get")
    async def test_error_3(self, mock_get, processor, async_session):
        # Prepare data
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_1
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_2
        _token_list_item.token_template = "ibetBond"
        _token_list_item.key_manager = ["0000000000000"]
        _token_list_item.product_type = 1
        async_session.add(_token_list_item)
        _token_list_item = TokenList()
        _token_list_item.token_address = self.token_address_3
        _token_list_item.token_template = "ibetShare"
        _token_list_item.key_manager = ["1111111111111"]
        _token_list_item.product_type = 5
        async_session.add(_token_list_item)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "token_address": self.token_address_4,
                        "token_template": "ibetShare",
                        "key_manager": ["0000000000000", "1111111111111"],
                        "product_type": 1,
                    },
                    "aaaaaaaa",  # not dict
                ]
            )
        ]

        # Run target process
        processor.process()

        # Assertion
        _token_list: Sequence[TokenList] = (
            await async_session.scalars(
                select(TokenList).order_by(TokenList.token_address)
            )
        ).all()
        assert len(_token_list) == 1
