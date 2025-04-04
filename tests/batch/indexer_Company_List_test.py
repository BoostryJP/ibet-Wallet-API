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

import asyncio
import json
import logging
from typing import Sequence
from unittest import mock
from unittest.mock import MagicMock

import pytest
import requests
from sqlalchemy import select

from app.model.db import Company
from batch.indexer_Company_List import LOG, Processor


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
        self.status = status_code

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self

    async def json(self) -> object:
        return self.data


class TestProcessor:
    ###########################################################################
    # Normal Case
    ###########################################################################

    # <Normal_1>
    # 0 record
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_1(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([])]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        session.rollback()
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 0

    # <Normal_2>
    # 1 record
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_2(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_3>
    # 2 record
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_3(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": None,
                    },
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000002",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 2
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == ""
        _company = _company_list[1]
        assert (
            _company.address == "0x0123456789AbCdEf0123456789aBcDEF00000002"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト2"
        assert _company.rsa_publickey == "RSA-KEY 2"
        assert _company.homepage == ""

    # <Normal_4_1_1>
    # Insert SKIP
    # type error
    # address
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_1_1(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": 12345,
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_1_2>
    # Insert SKIP
    # type error
    # corporate_name
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_1_2(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000002",
                        "corporate_name": 12345,
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_1_3>
    # Insert SKIP
    # type error
    # rsa_publickey
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_1_3(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000002",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": 12345,
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_1_4>
    # Insert SKIP
    # type error
    # homepage
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_1_4(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000002",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": 12345,
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_2_1>
    # Insert SKIP
    # required error
    # address
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_2_1(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_2_2>
    # Insert SKIP
    # required error
    # corporate_name
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_2_2(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000002",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_2_3>
    # Insert SKIP
    # required error
    # address
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_2_3(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000002",
                        "corporate_name": "株式会社テスト2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_4_3>
    # Insert SKIP
    # invalid address error
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_4_3(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x01",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1
        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

    # <Normal_5_1>
    # There are no differences from last time
    # -> Skip this cycle
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_5_1(self, mock_get, processor, session, caplog):
        # Run target process: 1st time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789AbCdEf0123456789aBcDEF00000002",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]
        asyncio.run(processor.process())

        # Run target process: 2nd time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789AbCdEf0123456789aBcDEF00000002",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 2

        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

        _company = _company_list[1]
        assert (
            _company.address == "0x0123456789AbCdEf0123456789aBcDEF00000002"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト2"
        assert _company.rsa_publickey == "RSA-KEY 2"
        assert _company.homepage == "http://test2.com"

        assert 1 == caplog.record_tuples.count(
            (
                LOG.name,
                logging.INFO,
                "Skip: There are no differences from the previous cycle",
            )
        )

    # <Normal_5_2>
    # There are differences from the previous cycle
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_normal_5_2(self, mock_get, processor, session, caplog):
        # Run target process: 1st time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    {
                        "address": "0x0123456789AbCdEf0123456789aBcDEF00000002",
                        "corporate_name": "株式会社テスト2",
                        "rsa_publickey": "RSA-KEY 2",
                        "homepage": "http://test2.com",
                    },
                ]
            )
        ]
        asyncio.run(processor.process())

        # Run target process: 2nd time
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                ]
            )
        ]
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 1

        _company = _company_list[0]
        assert (
            _company.address == "0x0123456789ABCdef0123456789aBcDeF00000001"
        )  # checksum address
        assert _company.corporate_name == "株式会社テスト1"
        assert _company.rsa_publickey == "RSA-KEY 1"
        assert _company.homepage == "http://test1.com"

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
    # API error
    # Connection error
    @mock.patch(
        "aiohttp.client.ClientSession.get",
        MagicMock(side_effect=requests.exceptions.ConnectionError),
    )
    def test_error_1_1(self, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 3

    # <Error_1_2>
    # API error
    # not succeed api
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_error_1_2(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [MockResponse([], 400)]

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 3

    # <Error_2>
    # not decode response
    @mock.patch(
        "aiohttp.client.ClientSession.get",
        MagicMock(side_effect=json.decoder.JSONDecodeError),
    )
    def test_error_2(self, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Run target process
        asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 3

    # <Error_3>
    # other error
    @mock.patch("aiohttp.client.ClientSession.get")
    def test_error_3(self, mock_get, processor, session):
        # Prepare data
        _company = Company()
        _company.address = "0x01"
        _company.corporate_name = "dummy1"
        _company.rsa_publickey = "dummy1"
        _company.homepage = "dummy1"
        session.add(_company)
        _company = Company()
        _company.address = "0x02"
        _company.corporate_name = "dummy2"
        _company.rsa_publickey = "dummy2"
        _company.homepage = "dummy2"
        session.add(_company)
        _company = Company()
        _company.address = "0x03"
        _company.corporate_name = "dummy3"
        _company.rsa_publickey = "dummy3"
        _company.homepage = "dummy3"
        session.add(_company)
        session.commit()

        # Mock
        mock_get.side_effect = [
            MockResponse(
                [
                    {
                        "address": "0x0123456789abcdef0123456789abcdef00000001",
                        "corporate_name": "株式会社テスト1",
                        "rsa_publickey": "RSA-KEY 1",
                        "homepage": "http://test1.com",
                    },
                    "aaaaaaaa",  # not dict
                ]
            )
        ]

        # Run target process
        with pytest.raises(Exception):
            asyncio.run(processor.process())

        # Assertion
        _company_list: Sequence[Company] = session.scalars(
            select(Company).order_by(Company.created)
        ).all()
        assert len(_company_list) == 3
