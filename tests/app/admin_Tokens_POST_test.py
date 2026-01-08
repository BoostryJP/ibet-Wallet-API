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
from typing import Any

from eth_utils.address import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.model.db import ExecutableContract, IDXBondToken, IDXPosition, Listing
from tests.account_config import eth_account
from tests.contract_modules import issue_bond_token, register_bond_list
from tests.types import DeployedContract, SharedContract
from tests.utils.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestAdminTokensPOST:
    # Test API
    apiurl = "/Admin/Tokens"

    @staticmethod
    def bond_token_attribute(
        exchange_address: str, personal_info_address: str
    ) -> dict[str, Any]:
        attribute = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange_address,
            "faceValue": 10000,
            "interestRate": 602,
            "interestPaymentDate1": "0101",
            "interestPaymentDate2": "0201",
            "interestPaymentDate3": "0301",
            "interestPaymentDate4": "0401",
            "interestPaymentDate5": "0501",
            "interestPaymentDate6": "0601",
            "interestPaymentDate7": "0701",
            "interestPaymentDate8": "0801",
            "interestPaymentDate9": "0901",
            "interestPaymentDate10": "1001",
            "interestPaymentDate11": "1101",
            "interestPaymentDate12": "1201",
            "redemptionDate": "20191231",
            "redemptionValue": 10000,
            "returnDate": "20191231",
            "returnAmount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "memo": "メモ",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "personalInfoAddress": personal_info_address,
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
        }
        return attribute

    @staticmethod
    def tokenlist_contract() -> DeployedContract:
        deployer = eth_account["deployer"]
        web3.eth.default_account = deployer["account_address"]
        contract_address, abi = Contract.deploy_contract(
            "TokenList", [], deployer["account_address"]
        )

        contract_address_str = str(contract_address)
        return {"address": contract_address_str, "abi": abi}

    @staticmethod
    def insert_listing_data(session: Session, _token: dict[str, Any]):
        token = Listing()
        token.token_address = _token["token_address"]
        token.is_public = _token["is_public"]
        token.max_holding_quantity = _token["max_holding_quantity"]
        token.max_sell_amount = _token["max_sell_amount"]
        token.owner_address = "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b"
        session.add(token)

    @staticmethod
    def insert_executable_contract_data(session: Session, _contract: dict[str, Any]):
        contract = ExecutableContract()
        contract.contract_address = _contract["contract_address"]
        session.add(contract)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1_1>
    # Normal request
    def test_normal_1_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        # Call API
        req_params = {
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "contract_address": bond_token["address"],
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "tradable_exchange": exchange_address,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "status": True,
                "max_holding_quantity": 100,
                "max_sell_amount": 50000,
                "personal_info_address": personal_info,
                "require_personal_info_registered": True,
                "transferable": True,
                "is_offering": False,
                "transfer_approval_required": False,
                "face_value": 10000,
                "face_value_currency": "JPY",
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
                "interest_payment_currency": "JPY",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "memo": "メモ",
                "is_redeemed": False,
            }
        }

        listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == req_params["contract_address"])
            .limit(1)
        ).first()
        assert listing is not None
        assert listing.token_address == req_params["contract_address"]
        assert listing.is_public == req_params["is_public"]
        assert listing.max_holding_quantity == req_params["max_holding_quantity"]
        assert listing.max_sell_amount == req_params["max_sell_amount"]
        assert listing.owner_address == issuer["account_address"]

        executable_contract = session.scalars(
            select(ExecutableContract)
            .where(
                ExecutableContract.contract_address == req_params["contract_address"]
            )
            .limit(1)
        ).first()
        assert executable_contract is not None
        assert executable_contract.contract_address == req_params["contract_address"]

        bond = session.scalars(select(IDXBondToken).limit(1)).first()
        assert bond is not None
        assert bond.token_address == req_params["contract_address"]
        assert bond.owner_address == issuer["account_address"]

        position = session.scalars(select(IDXPosition).limit(1)).first()
        assert position is not None
        assert position.token_address == req_params["contract_address"]
        assert position.account_address == issuer["account_address"]
        assert position.balance == 1000000

    # <Normal_1_2>
    # No settings for optional items
    def test_normal_1_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        # Call API
        req_params = {
            "is_public": True,
            "contract_address": bond_token["address"],
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "tradable_exchange": exchange_address,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "status": True,
                "max_holding_quantity": None,
                "max_sell_amount": None,
                "personal_info_address": personal_info,
                "require_personal_info_registered": True,
                "transferable": True,
                "is_offering": False,
                "transfer_approval_required": False,
                "face_value": 10000,
                "face_value_currency": "JPY",
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
                "interest_payment_currency": "JPY",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "memo": "メモ",
                "is_redeemed": False,
            }
        }

        listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == bond_token["address"])
            .limit(1)
        ).first()
        assert listing is not None
        assert listing.token_address == bond_token["address"]
        assert listing.is_public == req_params["is_public"]
        assert listing.max_holding_quantity is None
        assert listing.max_sell_amount is None
        assert listing.owner_address == issuer["account_address"]

        bond = session.scalars(select(IDXBondToken).limit(1)).first()
        assert bond is not None
        assert bond.token_address == bond_token["address"]
        assert bond.owner_address == issuer["account_address"]

        position = session.scalars(select(IDXPosition).limit(1)).first()
        assert position is not None
        assert position.token_address == bond_token["address"]
        assert position.account_address == issuer["account_address"]
        assert position.balance == 1000000

    # <Normal_2>
    # If balance data already exists, it will be overwritten.
    def test_normal_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        bf_position = IDXPosition()
        bf_position.token_address = bond_token["address"]
        bf_position.account_address = issuer["account_address"]
        bf_position.balance = 1000000
        session.add(bf_position)
        session.commit()

        # Call API
        req_params = {
            "is_public": True,
            "contract_address": bond_token["address"],
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "tradable_exchange": exchange_address,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "status": True,
                "max_holding_quantity": None,
                "max_sell_amount": None,
                "personal_info_address": personal_info,
                "require_personal_info_registered": True,
                "transferable": True,
                "is_offering": False,
                "transfer_approval_required": False,
                "face_value": 10000,
                "face_value_currency": "JPY",
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
                "interest_payment_currency": "JPY",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "memo": "メモ",
                "is_redeemed": False,
            }
        }

        listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == bond_token["address"])
            .limit(1)
        ).first()
        assert listing is not None
        assert listing.token_address == bond_token["address"]
        assert listing.is_public == req_params["is_public"]
        assert listing.max_holding_quantity is None
        assert listing.max_sell_amount is None
        assert listing.owner_address == issuer["account_address"]

        bond = session.scalars(select(IDXBondToken).limit(1)).first()
        assert bond is not None
        assert bond.token_address == bond_token["address"]
        assert bond.owner_address == issuer["account_address"]

        position = session.scalars(select(IDXPosition).limit(1)).first()
        assert position is not None
        assert position.token_address == bond_token["address"]
        assert position.account_address == issuer["account_address"]
        assert position.balance == 1000000

    # <Normal_3>
    # skip_conflict_error = True
    def test_normal_3(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        token = {
            "token_address": bond_token["address"],
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
        }
        self.insert_listing_data(session, token)
        session.commit()

        # Call API
        req_params = {
            "is_public": True,
            "contract_address": bond_token["address"],
            "skip_conflict_error": True,
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "tradable_exchange": exchange_address,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "status": True,
                "max_holding_quantity": 100,
                "max_sell_amount": 50000,
                "personal_info_address": personal_info,
                "require_personal_info_registered": True,
                "transferable": True,
                "is_offering": False,
                "transfer_approval_required": False,
                "face_value": 10000,
                "face_value_currency": "JPY",
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
                "interest_payment_currency": "JPY",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "memo": "メモ",
                "is_redeemed": False,
            }
        }

    ###########################################################################
    # Error
    ###########################################################################
    # ＜Error_1_1＞
    # 400（InvalidParameterError）
    # - No input params
    def test_error_1_1(self, client: TestClient, session: Session):
        request_params: dict[str, str] = {}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": {},
                    "loc": ["body", "contract_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": {},
                    "loc": ["body", "is_public"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # ＜Error_1_2＞
    # 400（InvalidParameterError）
    # - Invalid contract_address
    def test_error_1_2(self, client: TestClient, session: Session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7",  # アドレスが短い
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["body", "contract_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7",
                    "ctx": {"error": {}},
                }
            ],
        }

    # ＜Error_1_3＞
    # 400（InvalidParameterError）
    # - Invalid type params
    def test_error_1_3(self, client: TestClient, session: Session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": "Trueee",
            "max_holding_quantity": "aaaa",
            "max_sell_amount": "bbbb",
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "bool_parsing",
                    "loc": ["body", "is_public"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "input": "Trueee",
                },
                {
                    "type": "int_parsing",
                    "loc": ["body", "max_holding_quantity"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "aaaa",
                },
                {
                    "type": "int_parsing",
                    "loc": ["body", "max_sell_amount"],
                    "msg": "Input should be a valid integer, unable to parse string as an integer",
                    "input": "bbbb",
                },
            ],
        }

    # ＜Error_1_4＞
    # 400（InvalidParameterError）
    # - Validation error
    def test_error_1_4(self, client: TestClient, session: Session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": -1,
            "max_sell_amount": -1,
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "max_holding_quantity"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "max_sell_amount"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
            "message": "Invalid Parameter",
        }

    # <Error_2_1>
    # DataConflictError (listing)
    def test_error_2_1(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        token = {
            "token_address": bond_token["address"],
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
        }
        self.insert_listing_data(session, token)
        session.commit()

        # Call API
        req_params = {
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "contract_address": bond_token["address"],
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 409
        assert resp.json()["meta"] == {
            "code": 40,
            "message": "Data Conflict",
            "description": "contract_address already exist",
        }

    # <Error_2_2>
    # DataConflictError (executable_contract)
    def test_error_2_2(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        contract = {
            "contract_address": bond_token["address"],
        }
        self.insert_executable_contract_data(session, contract)
        session.commit()

        # Call API
        req_params = {
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "contract_address": bond_token["address"],
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 409
        assert resp.json()["meta"] == {
            "code": 40,
            "message": "Data Conflict",
            "description": "contract_address already exist",
        }

    # <Error_3>
    # Token is not available
    def test_error_3(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Bond token is disabled
        config.BOND_TOKEN_ENABLED = False

        # Prepare data
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        # Call API
        req_params = {
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
            "contract_address": bond_token["address"],
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "contract_address is invalid token address",
        }

    # <Error_4>
    # The specified `contract_address` is not registered in the TokenList.
    def test_error_4(
        self, client: TestClient, session: Session, shared_contract: SharedContract
    ):
        issuer = eth_account["issuer"]

        # Prepare data
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        exchange_address = to_checksum_address(
            shared_contract["IbetStraightBondExchange"]["address"]
        )
        personal_info = to_checksum_address(shared_contract["PersonalInfo"]["address"])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info
        )
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        # Call API
        req_params = {
            "contract_address": eth_account["issuer"]["account_address"],
            "is_public": True,
        }
        resp = client.post(self.apiurl, json=req_params)

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "contract_address is invalid token address",
        }
