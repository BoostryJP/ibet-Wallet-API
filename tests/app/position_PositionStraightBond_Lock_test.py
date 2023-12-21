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
import itertools

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.model.db import IDXBondToken, IDXLockedPosition

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionStraightBondLock:
    """
    Test Case for position.StraightBond.Lock
    """

    # テスト対象API
    apiurl_base = "/Position/{account_address}/StraightBond/Lock"

    issuer_address = "0x0000000000000000000000000000000000000001"
    exchange_address = "0x0000000000000000000000000000000000000002"
    personal_info_address = "0x0000000000000000000000000000000000000003"

    token_1 = "0xE883a6F441Ad5682D37Df31d34fC012bcb07A741"
    token_2 = "0xE883A6f441AD5682D37df31d34FC012bcB07a742"
    token_3 = "0xe883a6f441AD5682d37dF31D34fc012bCB07A743"

    lock_1 = "0x52D0784B3460E206Ed69393AE1f9eD37941089E1"
    lock_2 = "0x52D0784B3460E206Ed69393aE1f9eD37941089E2"
    lock_3 = "0x52D0784B3460E206ed69393ae1F9Ed37941089e3"

    account_1 = "0x15d34aaf54267dB7d7c367839aAf71A00A2C6A61"
    account_2 = "0x15D34aaF54267DB7d7c367839Aaf71a00a2C6a62"
    account_3 = "0x15D34AAF54267Db7d7c367839aAf71a00A2C6a63"

    @staticmethod
    def expected_token(token_address: str):
        return {
            "token_address": token_address,
            "owner_address": TestPositionStraightBondLock.issuer_address,
            "company_name": "",
            "rsa_publickey": "",
            "name": "テスト債券",
            "symbol": "BOND",
            "token_template": "IbetStraightBond",
            "total_supply": 1000000,
            "face_value": 10000,
            "interest_rate": 0.0602,
            "interest_payment_date1": "0101",
            "interest_payment_date2": "0201",
            "interest_payment_date3": "0301",
            "interest_payment_date4": "0401",
            "interest_payment_date5": "0501",
            "interest_payment_date6": "0601",
            "interest_payment_date7": "0701",
            "interest_payment_date8": "0801",
            "interest_payment_date9": "0901",
            "interest_payment_date10": "1001",
            "interest_payment_date11": "1101",
            "interest_payment_date12": "1201",
            "redemption_date": "20191231",
            "redemption_value": 10000,
            "return_date": "20191231",
            "return_amount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "max_holding_quantity": 1,
            "max_sell_amount": 1000,
            "contact_information": "問い合わせ先",
            "privacy_policy": "プライバシーポリシー",
            "is_redeemed": False,
            "transferable": True,
            "is_offering": False,
            "tradable_exchange": TestPositionStraightBondLock.exchange_address,
            "status": True,
            "memo": "メモ",
            "personal_info_address": TestPositionStraightBondLock.personal_info_address,
            "transfer_approval_required": False,
            "face_value_currency": "",
            "interest_payment_currency": "",
            "redemption_value_currency": "",
            "base_fx_rate": 0.0,
        }

    @staticmethod
    def create_idx_token(
        session: Session,
        token_address: str,
        issuer_address: str,
        personal_info_address: str,
        exchange_address: str | None,
    ):
        # Issue token
        idx_token = IDXBondToken()
        idx_token.token_address = token_address
        idx_token.owner_address = issuer_address
        idx_token.company_name = ""
        idx_token.rsa_publickey = ""
        idx_token.name = "テスト債券"
        idx_token.symbol = "BOND"
        idx_token.token_template = "IbetStraightBond"
        idx_token.total_supply = 1000000
        idx_token.face_value = 10000
        idx_token.interest_rate = 0.0602
        idx_token.interest_payment_date = [
            "0101",
            "0201",
            "0301",
            "0401",
            "0501",
            "0601",
            "0701",
            "0801",
            "0901",
            "1001",
            "1101",
            "1201",
        ]
        idx_token.redemption_date = "20191231"
        idx_token.redemption_value = 10000
        idx_token.return_date = "20191231"
        idx_token.return_amount = "商品券をプレゼント"
        idx_token.purpose = "新商品の開発資金として利用。"
        idx_token.max_holding_quantity = 1
        idx_token.max_sell_amount = 1000
        idx_token.contact_information = "問い合わせ先"
        idx_token.privacy_policy = "プライバシーポリシー"
        idx_token.is_redeemed = False
        idx_token.transferable = True
        idx_token.is_offering = False
        idx_token.tradable_exchange = exchange_address
        idx_token.status = True
        idx_token.memo = "メモ"
        idx_token.personal_info_address = personal_info_address
        idx_token.transfer_approval_required = False
        idx_token.face_value_currency = ""
        idx_token.interest_payment_currency = ""
        idx_token.redemption_value_currency = ""
        idx_token.base_fx_rate = 0.0
        session.add(idx_token)
        session.commit()

    @staticmethod
    def create_idx_locked(
        session: Session,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
    ):
        # Issue token
        idx_locked = IDXLockedPosition()
        idx_locked.token_address = token_address
        idx_locked.lock_address = lock_address
        idx_locked.account_address = account_address
        idx_locked.value = value
        session.add(idx_locked)
        session.commit()

    def setup_data(self, session: Session):
        token_address_list = [self.token_1, self.token_2, self.token_3]
        lock_address_list = [self.lock_1, self.lock_2, self.lock_3]
        account_address_list = [self.account_1, self.account_2, self.account_3]

        [
            self.create_idx_token(
                session=session,
                token_address=token_address,
                issuer_address=self.issuer_address,
                exchange_address=self.exchange_address,
                personal_info_address=self.personal_info_address,
            )
            for token_address in token_address_list
        ]

        for value, (token_address, lock_address, account_address) in enumerate(
            itertools.product(
                token_address_list, lock_address_list, account_address_list
            )
        ):
            self.create_idx_locked(
                session=session,
                token_address=token_address,
                lock_address=lock_address,
                account_address=account_address,
                value=value + 1,
            )

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # List all tokens
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_1_1(self, get_params, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={**get_params},
        )

        assumed_body = {
            "result_set": {"count": 9, "offset": None, "limit": None, "total": 9},
            "locked_positions": [
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 4,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 7,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 13,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 16,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 19,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 22,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 25,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_1_2>
    # List specific tokens with query
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_1_2(self, get_params, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={**get_params, "token_address_list": [self.token_1, self.token_2]},
        )

        assumed_body = {
            "result_set": {"count": 6, "offset": None, "limit": None, "total": 6},
            "locked_positions": [
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 4,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 7,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 13,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 16,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_2>
    # Pagination
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_2(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                **get_params,
                "token_address_list": [self.token_1],
                "offset": 1,
                "limit": 2,
            },
        )

        assumed_body = {
            "result_set": {"count": 3, "offset": 1, "limit": 2, "total": 3},
            "locked_positions": [
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 4,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 7,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_3>
    # Pagination(over offset)
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_3(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={**get_params, "token_address_list": [self.token_1], "offset": 9},
        )

        assumed_body = {
            "result_set": {"count": 3, "offset": 9, "limit": None, "total": 3},
            "locked_positions": [],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_4>
    # Filter(lock_address)
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_4(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={**get_params, "lock_address": self.lock_1},
        )

        assumed_body = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 9},
            "locked_positions": [
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 19,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_1>
    # Sort(token_address)
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_5_1(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={**get_params, "sort_order": 1, "sort_item": "token_address"},
        )

        assumed_body = {
            "result_set": {"count": 9, "offset": None, "limit": None, "total": 9},
            "locked_positions": [
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 19,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 22,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 25,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 13,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 16,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 4,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 7,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_2>
    # Sort(lock_address)
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_5_2(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={**get_params, "sort_order": 0, "sort_item": "lock_address"},
        )

        assumed_body = {
            "result_set": {"count": 9, "offset": None, "limit": None, "total": 9},
            "locked_positions": [
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 19,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 4,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 13,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_2,
                    "account_address": self.account_1,
                    "value": 22,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 7,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 16,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_3,
                    "account_address": self.account_1,
                    "value": 25,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_3>
    # Sort(account_address)
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_5_3(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                **get_params,
                "lock_address": self.lock_1,
                "sort_order": 0,
                "sort_item": "account_address",
            },
        )

        assumed_body = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 9},
            "locked_positions": [
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 19,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # <Normal_5_4>
    # Sort(value)
    @pytest.mark.parametrize(
        "get_params",
        [
            {"include_token_details": True},
            {"include_token_details": False},
            {},
        ],
    )
    def test_normal_5_4(
        self, get_params, client: TestClient, session: Session, shared_contract
    ):
        config.BOND_TOKEN_ENABLED = True

        # Prepare Data
        self.setup_data(session)

        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                **get_params,
                "lock_address": self.lock_1,
                "sort_order": 1,
                "sort_item": "value",
            },
        )

        assumed_body = {
            "result_set": {"count": 3, "offset": None, "limit": None, "total": 9},
            "locked_positions": [
                {
                    "token_address": self.token_3,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 19,
                },
                {
                    "token_address": self.token_2,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 10,
                },
                {
                    "token_address": self.token_1,
                    "lock_address": self.lock_1,
                    "account_address": self.account_1,
                    "value": 1,
                },
            ],
        }
        if get_params.get("include_token_details") is True:
            assumed_body["locked_positions"] = [
                {**b, "token": self.expected_token(b["token_address"])}
                for b in assumed_body["locked_positions"]
            ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # ParameterError: invalid account_address
    def test_error_1(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address="invalid"),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "account_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "invalid",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_2>
    # ParameterError: offset/limit(minus value)
    def test_error_2(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "offset": -1,
                "limit": -1,
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
            "message": "Invalid Parameter",
        }

    # <Error_3>
    # ParameterError: offset/limit(not int), include_token_details(not bool)
    def test_error_3(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
            params={
                "offset": "test",
                "limit": "test",
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "test",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # <Error_4>
    # Not Supported
    def test_error_4(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = False

        # Request target API
        resp = client.get(
            self.apiurl_base.format(account_address=self.account_1),
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /Position/0x15d34aaf54267dB7d7c367839aAf71A00A2C6A61/StraightBond/Lock",
        }
