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

from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import ExecutableContract, IDXBondToken, IDXPosition, Listing
from tests.account_config import eth_account
from tests.contract_modules import issue_bond_token, register_bond_list

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAdminTokensPOST:
    # テスト対象API
    apiurl = "/Admin/Tokens"

    token_param_1 = {
        "is_public": True,
        "max_holding_quantity": 100,
        "max_sell_amount": 50000,
    }

    token_param_2 = {
        "is_public": True,
    }

    @staticmethod
    def bond_token_attribute(exchange_address, personal_info_address):
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
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account["deployer"]
        web3.eth.default_account = deployer["account_address"]
        contract_address, abi = Contract.deploy_contract(
            "TokenList", [], deployer["account_address"]
        )

        return {"address": contract_address, "abi": abi}

    @staticmethod
    def insert_listing_data(session, _token):
        token = Listing()
        token.token_address = _token["token_address"]
        token.is_public = _token["is_public"]
        token.max_holding_quantity = _token["max_holding_quantity"]
        token.max_sell_amount = _token["max_sell_amount"]
        token.owner_address = "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b"
        session.add(token)

    @staticmethod
    def insert_executable_contract_data(session, _contract):
        contract = ExecutableContract()
        contract.contract_address = _contract["contract_address"]
        session.add(contract)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = self.token_param_1
        request_params["contract_address"] = bond_token["address"]
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        listing: Listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == self.token_param_1["contract_address"])
            .limit(1)
        ).first()
        assert listing.token_address == self.token_param_1["contract_address"]
        assert listing.is_public == self.token_param_1["is_public"]
        assert (
            listing.max_holding_quantity == self.token_param_1["max_holding_quantity"]
        )
        assert listing.max_sell_amount == self.token_param_1["max_sell_amount"]
        assert listing.owner_address == issuer["account_address"]

        executable_contract: ExecutableContract = session.scalars(
            select(ExecutableContract)
            .where(
                ExecutableContract.contract_address
                == self.token_param_1["contract_address"]
            )
            .limit(1)
        ).first()
        assert (
            executable_contract.contract_address
            == self.token_param_1["contract_address"]
        )

        bond: IDXBondToken = session.scalars(select(IDXBondToken).limit(1)).first()
        assert bond.token_address == self.token_param_1["contract_address"]
        assert bond.owner_address == issuer["account_address"]

        position: IDXPosition = session.scalars(select(IDXPosition).limit(1)).first()
        assert position.token_address == self.token_param_1["contract_address"]
        assert position.account_address == issuer["account_address"]
        assert position.balance == 1000000

    # <Normal_2>
    # 任意設定項目なし
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = self.token_param_2
        request_params["contract_address"] = bond_token["address"]
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        listing: Listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == bond_token["address"])
            .limit(1)
        ).first()
        assert listing.token_address == bond_token["address"]
        assert listing.is_public == self.token_param_2["is_public"]
        assert listing.max_holding_quantity is None
        assert listing.max_sell_amount is None
        assert listing.owner_address == issuer["account_address"]

        bond: IDXBondToken = session.scalars(select(IDXBondToken).limit(1)).first()
        assert bond.token_address == bond_token["address"]
        assert bond.owner_address == issuer["account_address"]

        position: IDXPosition = session.scalars(select(IDXPosition).limit(1)).first()
        assert position.token_address == bond_token["address"]
        assert position.account_address == issuer["account_address"]
        assert position.balance == 1000000

    # <Normal_3>
    # Position data has already indexed
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = self.token_param_2
        request_params["contract_address"] = bond_token["address"]
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}

        listing: Listing = session.scalars(
            select(Listing)
            .where(Listing.token_address == bond_token["address"])
            .limit(1)
        ).first()
        assert listing.token_address == bond_token["address"]
        assert listing.is_public == self.token_param_2["is_public"]
        assert listing.max_holding_quantity is None
        assert listing.max_sell_amount is None
        assert listing.owner_address == issuer["account_address"]

        bond: IDXBondToken = session.scalars(select(IDXBondToken).limit(1)).first()
        assert bond.token_address == bond_token["address"]
        assert bond.owner_address == issuer["account_address"]

        position: IDXPosition = session.scalars(select(IDXPosition).limit(1)).first()
        assert position.token_address == bond_token["address"]
        assert position.account_address == issuer["account_address"]
        assert position.balance == 1000000

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # headersなし
    # 400（InvalidParameterError）
    def test_error_1(self, client: TestClient, session: Session):
        request_params = self.token_param_1
        headers: dict[str, str] = {}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": "contract_address is invalid token address",
            "message": "Invalid Parameter",
        }

    # ＜Error_2＞
    # 入力値なし
    # 400（InvalidParameterError）
    def test_error_2(self, client: TestClient, session: Session):
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
                    "url": "https://errors.pydantic.dev/2.1/v/missing",
                },
                {
                    "input": {},
                    "loc": ["body", "is_public"],
                    "msg": "Field required",
                    "type": "missing",
                    "url": "https://errors.pydantic.dev/2.1/v/missing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # ＜Error_3_1＞
    # contract_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_3_1(self, client: TestClient, session: Session):
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
            "description": [
                {
                    "ctx": {"error": {}},
                    "input": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7",
                    "loc": ["body", "contract_address"],
                    "msg": "Value error, token_address is not a valid address",
                    "type": "value_error",
                    "url": "https://errors.pydantic.dev/2.1/v/value_error",
                }
            ],
            "message": "Invalid Parameter",
        }

    # ＜Error_3_2＞
    # 入力値の型誤り
    # 400（InvalidParameterError）
    def test_error_3_2(self, client: TestClient, session: Session):
        request_params = {
            "contract_address": 1234,
            "is_public": "True",
            "max_holding_quantity": "100",
            "max_sell_amount": "50000",
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": 1234,
                    "loc": ["body", "contract_address"],
                    "msg": "Input should be a valid string",
                    "type": "string_type",
                    "url": "https://errors.pydantic.dev/2.1/v/string_type",
                }
            ],
            "message": "Invalid Parameter",
        }

    # ＜Error_3_3＞
    # 最小値チェック
    # 400（InvalidParameterError）
    def test_error_3_3(self, client: TestClient, session: Session):
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
                    "url": "https://errors.pydantic.dev/2.1/v/greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": -1,
                    "loc": ["body", "max_sell_amount"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                    "url": "https://errors.pydantic.dev/2.1/v/greater_than_equal",
                },
            ],
            "message": "Invalid Parameter",
        }

    # <Error_4>
    # 指定のcontract_addressのレコードが listing テーブルに既に登録済
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = self.token_param_1
        request_params["contract_address"] = bond_token["address"]
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 409
        assert resp.json()["meta"] == {
            "code": 40,
            "message": "Data Conflict",
            "description": "contract_address already exist",
        }

    # <Error_5>
    # 指定のcontract_addressのレコードが executable_contract テーブルに既に登録済
    def test_error_5(self, client: TestClient, session: Session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = self.token_param_1
        request_params["contract_address"] = bond_token["address"]
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 409
        assert resp.json()["meta"] == {
            "code": 40,
            "message": "Data Conflict",
            "description": "contract_address already exist",
        }

    # <Error_6>
    # 指定のcontract_addressが取扱していないtoken_template
    def test_error_6(self, client: TestClient, session: Session, shared_contract):
        # 債券トークン取扱無し
        config.BOND_TOKEN_ENABLED = False

        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = self.token_param_1
        request_params["contract_address"] = bond_token["address"]
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "contract_address is invalid token address",
        }

    # <Error_7>
    # 指定のcontract_addressがTokenListに未登録のtoken_address
    def test_error_7(self, client: TestClient, session: Session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account["issuer"]

        # [事前準備]tokenの発行(TokenListへの登録のみ)
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

        request_params = {
            "contract_address": eth_account["issuer"]["account_address"],
            "is_public": True,
        }

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "contract_address is invalid token address",
        }
