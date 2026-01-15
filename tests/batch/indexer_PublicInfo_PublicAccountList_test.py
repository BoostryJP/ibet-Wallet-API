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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.db import PublicAccountList
from batch.indexer_PublicInfo_PublicAccountList import LOG, Processor


@pytest.fixture(scope="function")
def processor():
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


@mock.patch(
    "batch.indexer_PublicInfo_PublicAccountList.PUBLIC_ACCOUNT_LIST_URL",
    "http://test/public_account_list.json",
)
@pytest.mark.asyncio
class TestProcessor:
    test_key_manager_1 = "test_key_manager_1"
    test_key_manager_name_1 = "test_key_manager_name_1"
    test_account_address_1 = "0x16f39D63d156f9abCe0a9aB46F751E2eFdEB040f"

    test_key_manager_2 = "test_key_manager_2"
    test_key_manager_name_2 = "test_key_manager_name_2"
    test_account_address_2 = "0x28e0ad30c43B3D55851b881E25586926894de3e9"

    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @mock.patch("requests.Session.get")
    async def test_normal_1(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
    ):
        # Prepare data
        _account_list = PublicAccountList()
        _account_list.key_manager = self.test_key_manager_1
        _account_list.key_manager_name = self.test_key_manager_name_1
        _account_list.account_type = 1
        _account_list.account_address = self.test_account_address_1
        async_session.add(_account_list)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([])]

        # Run target process
        processor.process()

        # Assertion
        # - The cleanup process should remove all data.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(select(PublicAccountList))
        ).all()
        assert len(_account_list_af) == 0

    # <Normal_2>
    # Multiple records
    @mock.patch("requests.Session.get")
    async def test_normal_2(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
    ):
        # Prepare data
        _account_list = PublicAccountList()
        _account_list.key_manager = self.test_key_manager_1
        _account_list.key_manager_name = self.test_key_manager_name_1
        _account_list.account_type = 1
        _account_list.account_address = self.test_account_address_1
        async_session.add(_account_list)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "key_manager": self.test_key_manager_1,
                        "key_manager_name": self.test_key_manager_name_1,
                        "type": 2,
                        "account_address": self.test_account_address_1,
                    },
                    {
                        "key_manager": self.test_key_manager_2,
                        "key_manager_name": self.test_key_manager_name_2,
                        "type": 3,
                        "account_address": self.test_account_address_2,
                    },
                ]
            )
        ]

        # Run target process
        processor.process()

        # Assertion
        # - The cleanup process should remove all data.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 2

        assert _account_list_af[0].json() == {
            "key_manager": self.test_key_manager_1,
            "key_manager_name": self.test_key_manager_name_1,
            "account_type": 2,
            "account_address": self.test_account_address_1,
            "modified": mock.ANY,
        }
        assert _account_list_af[1].json() == {
            "key_manager": self.test_key_manager_2,
            "key_manager_name": self.test_key_manager_name_2,
            "account_type": 3,
            "account_address": self.test_account_address_2,
            "modified": mock.ANY,
        }

    # <Normal_3_1>
    # There are no differences from last time
    # -> Skip this cycle
    @mock.patch("requests.Session.get")
    async def test_normal_3_1(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        # Run target process: 1st time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "key_manager": self.test_key_manager_1,
                        "key_manager_name": self.test_key_manager_name_1,
                        "type": 1,
                        "account_address": self.test_account_address_1,
                    },
                    {
                        "key_manager": self.test_key_manager_2,
                        "key_manager_name": self.test_key_manager_name_2,
                        "type": 2,
                        "account_address": self.test_account_address_2,
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
                        "key_manager": self.test_key_manager_1,
                        "key_manager_name": self.test_key_manager_name_1,
                        "type": 1,
                        "account_address": self.test_account_address_1,
                    },
                    {
                        "key_manager": self.test_key_manager_2,
                        "key_manager_name": self.test_key_manager_name_2,
                        "type": 2,
                        "account_address": self.test_account_address_2,
                    },
                ]
            )
        ]
        processor.process()

        # Assertion
        # - The cleanup process should remove all of your data.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 2

        assert _account_list_af[0].json() == {
            "key_manager": self.test_key_manager_1,
            "key_manager_name": self.test_key_manager_name_1,
            "account_type": 1,
            "account_address": self.test_account_address_1,
            "modified": mock.ANY,
        }
        assert _account_list_af[1].json() == {
            "key_manager": self.test_key_manager_2,
            "key_manager_name": self.test_key_manager_name_2,
            "account_type": 2,
            "account_address": self.test_account_address_2,
            "modified": mock.ANY,
        }

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                "Skip: There are no differences from the previous cycle",
            )
        )

    # <Normal_3_2>
    # There are differences from last time
    @mock.patch("requests.Session.get")
    async def test_normal_3_2(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
        caplog: pytest.LogCaptureFixture,
    ):
        # Run target process: 1st time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "key_manager": self.test_key_manager_1,
                        "key_manager_name": self.test_key_manager_name_1,
                        "type": 1,
                        "account_address": self.test_account_address_1,
                    },
                    {
                        "key_manager": self.test_key_manager_2,
                        "key_manager_name": self.test_key_manager_name_2,
                        "type": 2,
                        "account_address": self.test_account_address_2,
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
                        "key_manager": self.test_key_manager_1,
                        "key_manager_name": self.test_key_manager_name_1,
                        "type": 1,
                        "account_address": self.test_account_address_1,
                    },
                ]
            )
        ]
        processor.process()

        # Assertion
        # - The cleanup process should remove all data.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 1

        assert _account_list_af[0].json() == {
            "key_manager": self.test_key_manager_1,
            "key_manager_name": self.test_key_manager_name_1,
            "account_type": 1,
            "account_address": self.test_account_address_1,
            "modified": mock.ANY,
        }

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
    async def test_error_1_1(self, processor: Processor, async_session: AsyncSession):
        # Prepare data
        _account_list = PublicAccountList()
        _account_list.key_manager = self.test_key_manager_1
        _account_list.key_manager_name = self.test_key_manager_name_1
        _account_list.account_type = 1
        _account_list.account_address = self.test_account_address_1
        async_session.add(_account_list)
        await async_session.commit()

        # Run target process
        processor.process()

        # Assertion
        # - The cleanup process should be rolled back and
        #   the data should remain as it was before processing.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 1

        assert _account_list_af[0].json() == {
            "key_manager": self.test_key_manager_1,
            "key_manager_name": self.test_key_manager_name_1,
            "account_type": 1,
            "account_address": self.test_account_address_1,
            "modified": mock.ANY,
        }

    # <Error_1_2>
    # API error: Not succeed request
    @mock.patch("requests.Session.get")
    async def test_error_1_2(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
    ):
        # Prepare data
        _account_list = PublicAccountList()
        _account_list.key_manager = self.test_key_manager_1
        _account_list.key_manager_name = self.test_key_manager_name_1
        _account_list.account_type = 1
        _account_list.account_address = self.test_account_address_1
        async_session.add(_account_list)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([], 400)]

        # Run target process
        processor.process()

        # Assertion
        # - The cleanup process should be rolled back and
        #   the data should remain as it was before processing.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 1

        assert _account_list_af[0].json() == {
            "key_manager": self.test_key_manager_1,
            "key_manager_name": self.test_key_manager_name_1,
            "account_type": 1,
            "account_address": self.test_account_address_1,
            "modified": mock.ANY,
        }

    # <Error_1_3>
    # API error: JSONDecodeError
    @mock.patch(
        "requests.Session.get",
        MagicMock(side_effect=json.decoder.JSONDecodeError),
    )
    async def test_error_1_3(self, processor: Processor, async_session: AsyncSession):
        # Prepare data
        _account_list = PublicAccountList()
        _account_list.key_manager = self.test_key_manager_1
        _account_list.key_manager_name = self.test_key_manager_name_1
        _account_list.account_type = 1
        _account_list.account_address = self.test_account_address_1
        async_session.add(_account_list)
        await async_session.commit()

        # Run target process
        processor.process()

        # Assertion
        # - The cleanup process should be rolled back and
        #   the data should remain as it was before processing.
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 1

        assert _account_list_af[0].json() == {
            "key_manager": self.test_key_manager_1,
            "key_manager_name": self.test_key_manager_name_1,
            "account_type": 1,
            "account_address": self.test_account_address_1,
            "modified": mock.ANY,
        }

    # <Error_2>
    # Invalid type error
    # -> Skip processing
    @mock.patch("requests.Session.get")
    @pytest.mark.parametrize(
        "invalid_record",
        [
            {
                "key_manager": 123,  # Invalid key_manager
                "key_manager_name": test_key_manager_name_1,
                "type": 1,
                "account_address": test_account_address_1,
            },
            {
                "key_manager": test_key_manager_1,
                "key_manager_name": 123,  # Invalid key_manager_name
                "type": 1,
                "account_address": test_account_address_1,
            },
            {
                "key_manager": test_key_manager_1,
                "key_manager_name": test_key_manager_name_1,
                "type": "1",  # Invalid type
                "account_address": test_account_address_1,
            },
            {
                "key_manager": test_key_manager_1,
                "key_manager_name": test_key_manager_name_1,
                "type": 1,
                "account_address": 123,  # Invalid account_address (Type error)
            },
            {
                "key_manager": test_key_manager_1,
                "key_manager_name": test_key_manager_name_1,
                "type": 1,
                "account_address": "invalid_address",  # Invalid account_address (Not checksum address)
            },
            {
                "key_manager_name": test_key_manager_name_1,
                "type": 1,
                "account_address": test_account_address_1,
            },  # Missing required fields
            {
                "key_manager": test_key_manager_1,
                "type": 1,
                "account_address": test_account_address_1,
            },  # Missing required fields
            {
                "key_manager": test_key_manager_1,
                "key_manager_name": test_key_manager_name_1,
                "account_address": test_account_address_1,
            },  # Missing required fields
            {
                "key_manager": test_key_manager_1,
                "key_manager_name": test_key_manager_name_1,
                "type": 1,
            },  # Missing required fields
        ],
    )
    async def test_error_2(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
        invalid_record: dict[str, object],
    ):
        # Prepare data
        _account_list = PublicAccountList()
        _account_list.key_manager = self.test_key_manager_1
        _account_list.key_manager_name = self.test_key_manager_name_1
        _account_list.account_type = 1
        _account_list.account_address = self.test_account_address_1
        async_session.add(_account_list)
        await async_session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([invalid_record])]

        # Run target process
        processor.process()

        # Assertion
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 0

    # <Error_3>
    # Other error
    @mock.patch("requests.Session.get")
    async def test_error_3(
        self,
        mock_get: mock.MagicMock,
        processor: Processor,
        async_session: AsyncSession,
    ):
        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "key_manager": self.test_key_manager_1,
                        "key_manager_name": self.test_key_manager_name_1,
                        "type": 2,
                        "account_address": self.test_account_address_1,
                    },
                    "aaaaaaaa",  # not dict
                ]
            )
        ]

        # Run target process
        with pytest.raises(Exception):
            processor.process()

        # Assertion
        await async_session.rollback()
        _account_list_af: Sequence[PublicAccountList] = (
            await async_session.scalars(
                select(PublicAccountList).order_by(
                    PublicAccountList.key_manager, PublicAccountList.account_type
                )
            )
        ).all()
        assert len(_account_list_af) == 0
