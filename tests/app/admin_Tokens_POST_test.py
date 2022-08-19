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
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import (
    Listing,
    ExecutableContract
)
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestAdminTokensPOST:
    # テスト対象API
    apiurl = '/Admin/Tokens'

    token_1 = {
        "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
        "max_holding_quantity": 100,
        "max_sell_amount": 50000,
    }

    token_2 = {
        "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
        "is_public": True,
    }

    @staticmethod
    def bond_token_attribute(exchange_address, personal_info_address):
        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange_address,
            'faceValue': 10000,
            'interestRate': 602,
            'interestPaymentDate1': '0101',
            'interestPaymentDate2': '0201',
            'interestPaymentDate3': '0301',
            'interestPaymentDate4': '0401',
            'interestPaymentDate5': '0501',
            'interestPaymentDate6': '0601',
            'interestPaymentDate7': '0701',
            'interestPaymentDate8': '0801',
            'interestPaymentDate9': '0901',
            'interestPaymentDate10': '1001',
            'interestPaymentDate11': '1101',
            'interestPaymentDate12': '1201',
            'redemptionDate': '20191231',
            'redemptionValue': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'personalInfoAddress': personal_info_address
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.default_account = deployer['account_address']
        contract_address, abi = Contract.deploy_contract(
            'TokenList', [], deployer['account_address'])

        return {'address': contract_address, 'abi': abi}

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
    def test_normal_1(self, client, session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account['issuer']

        # [事前準備]tokenの発行(TokenListへの登録のみ)
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        exchange_address = to_checksum_address(
            shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(
            shared_contract['PersonalInfo']['address'])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        request_params = self.token_1
        request_params["contract_address"] = bond_token["address"]
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        listing = session.query(Listing). \
            filter(Listing.token_address == self.token_1["contract_address"]). \
            first()
        assert listing.token_address == self.token_1["contract_address"]
        assert listing.is_public == self.token_1["is_public"]
        assert listing.max_holding_quantity == self.token_1["max_holding_quantity"]
        assert listing.max_sell_amount == self.token_1["max_sell_amount"]
        assert listing.owner_address == issuer["account_address"]

        executable_contract = session.query(ExecutableContract). \
            filter(ExecutableContract.contract_address == self.token_1["contract_address"]). \
            first()
        assert executable_contract.contract_address == self.token_1["contract_address"]

    # <Normal_2>
    # 任意設定項目なし
    def test_normal_2(self, client, session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account['issuer']

        # [事前準備]tokenの発行(TokenListへの登録のみ)
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        exchange_address = to_checksum_address(
            shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(
            shared_contract['PersonalInfo']['address'])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        request_params = self.token_2
        request_params["contract_address"] = bond_token["address"]
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        listing = session.query(Listing). \
            filter(Listing.token_address == self.token_2["contract_address"]). \
            first()
        assert listing.token_address == self.token_2["contract_address"]
        assert listing.is_public == self.token_2["is_public"]
        assert listing.max_holding_quantity is None
        assert listing.max_sell_amount is None
        assert listing.owner_address == issuer["account_address"]

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # headersなし
    # 400（InvalidParameterError）
    def test_error_1(self, client, session):
        request_params = self.token_1
        headers = {}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜Error_2＞
    # 入力値なし
    # 400（InvalidParameterError）
    def test_error_2(self, client, session):
        request_params = {}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'contract_address': ['required field'],
                'is_public': ['required field'],
            }
        }

    # ＜Error_3_1＞
    # contract_addressのフォーマット誤り
    # 400（InvalidParameterError）
    def test_error_3_1(self, client, session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7",  # アドレスが短い
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid contract address'
        }

    # ＜Error_3_2＞
    # 入力値の型誤り
    # 400（InvalidParameterError）
    def test_error_3_2(self, client, session):
        request_params = {
            "contract_address": 1234,
            "is_public": "True",
            "max_holding_quantity": "100",
            "max_sell_amount": "50000",
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'contract_address': ['must be of string type'],
                'is_public': ['must be of boolean type'],
                'max_holding_quantity': ['must be of integer type'],
                'max_sell_amount': ['must be of integer type'],
            }
        }

    # ＜Error_3_3＞
    # 最小値チェック
    # 400（InvalidParameterError）
    def test_error_3_3(self, client, session):
        request_params = {
            "contract_address": "0x9467ABe171e0da7D6aBDdA23Ba6e6Ec5BE0b4F7b",
            "is_public": True,
            "max_holding_quantity": -1,
            "max_sell_amount": -1,
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'max_holding_quantity': ['min value is 0'],
                'max_sell_amount': ['min value is 0']
            }
        }

    # <Error_4>
    # 指定のcontract_addressのレコードが listing テーブルに既に登録済
    def test_error_4(self, client, session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account['issuer']

        # [事前準備]tokenの発行(TokenListへの登録のみ)
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        exchange_address = to_checksum_address(
            shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(
            shared_contract['PersonalInfo']['address'])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        token = {
            "token_address": bond_token["address"],
            "is_public": True,
            "max_holding_quantity": 100,
            "max_sell_amount": 50000,
        }
        self.insert_listing_data(session, token)

        request_params = self.token_1
        request_params["contract_address"] = bond_token["address"]
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 409
        assert resp.json['meta'] == {
            'code': 40,
            'message': 'Data Conflict',
            'description': 'contract_address already exist'
        }

    # <Error_5>
    # 指定のcontract_addressのレコードが executable_contract テーブルに既に登録済
    def test_error_5(self, client, session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account['issuer']

        # [事前準備]tokenの発行(TokenListへの登録のみ)
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        exchange_address = to_checksum_address(
            shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(
            shared_contract['PersonalInfo']['address'])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        contract = {
            "contract_address": bond_token["address"],
        }
        self.insert_executable_contract_data(session, contract)

        request_params = self.token_1
        request_params["contract_address"] = bond_token["address"]
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 409
        assert resp.json['meta'] == {
            'code': 40,
            'message': 'Data Conflict',
            'description': 'contract_address already exist'
        }

    # <Error_6>
    # 指定のcontract_addressが取扱していないtoken_template
    def test_error_6(self, client, session, shared_contract):
        # 債券トークン取扱無し
        config.BOND_TOKEN_ENABLED = False

        # テスト用発行体アカウント
        issuer = eth_account['issuer']

        # [事前準備]tokenの発行(TokenListへの登録のみ)
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        exchange_address = to_checksum_address(
            shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(
            shared_contract['PersonalInfo']['address'])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        request_params = self.token_1
        request_params["contract_address"] = bond_token["address"]
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'contract_address is invalid token address'
        }

    # <Error_7>
    # 指定のcontract_addressがTokenListに未登録のtoken_address
    def test_error_7(self, client, session, shared_contract):
        # テスト用発行体アカウント
        issuer = eth_account['issuer']

        # [事前準備]tokenの発行(TokenListへの登録のみ)
        config.BOND_TOKEN_ENABLED = True
        token_list = TestAdminTokensPOST.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        exchange_address = to_checksum_address(
            shared_contract['IbetStraightBondExchange']['address'])
        personal_info = to_checksum_address(
            shared_contract['PersonalInfo']['address'])
        attribute = TestAdminTokensPOST.bond_token_attribute(
            exchange_address, personal_info)
        bond_token = issue_bond_token(issuer, attribute)

        register_bond_list(issuer, bond_token, token_list)

        request_params = {
            "contract_address": eth_account['issuer']["account_address"],
            "is_public": True,
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'contract_address is invalid token address'
        }
