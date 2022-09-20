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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest import mock
from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config
from app.contracts import Contract

from app.model.db import (
    Listing,
    ExecutableContract
)

from tests.account_config import eth_account
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list, transfer_coupon_token
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def tokenlist_contract():
    issuer = eth_account['issuer']
    web3.eth.default_account = issuer['account_address']
    contract_address, abi = Contract.deploy_contract(
        'TokenList', [], issuer['account_address'])

    return {'address': contract_address, 'abi': abi}


def listing_token(session, token):
    listing = Listing()
    listing.token_address = token['address']
    listing.is_public = True
    listing.max_holding_quantity = 1
    listing.max_sell_amount = 1000
    session.add(listing)


def executable_contract_token(session, contract):
    executable_contract = ExecutableContract()
    executable_contract.contract_address = contract['address']
    session.add(executable_contract)


class TestEthWaitForTransactionReceipt:

    # テスト対象API
    apiurl = '/Eth/WaitForTransactionReceipt'

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Wait receipt for successful transaction
    def test_normal_1(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(issuer, {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "totalSupply": 1000000,
            "tradableExchange": config.ZERO_ADDRESS,
            "details": "details_test1",
            "returnDetails": "returnDetails_test1",
            "memo": "memo_test1",
            "expirationDate": "20211201",
            "transferable": True,
            "contactInformation": "contactInformation_test1",
            "privacyPolicy": "privacyPolicy_test1"
        })
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )
        user1 = eth_account["user1"]
        transfer_coupon_token(issuer, coupontoken_1, user1["account_address"], 10)

        tx = token_contract_1.functions.consume(10).build_transaction({
            "from": to_checksum_address(user1["account_address"]),
            "gas": 6000000,
            "gasPrice": 0
        })
        tx_hash = web3.eth.send_transaction(tx)
        request_params = {
            "transaction_hash": tx_hash.hex()
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            'code': 200,
            'message': "OK"
        }
        assert resp.json()["data"] == {
            "status": 1
        }

    # <Normal_2>
    # Wait receipt for reverted transaction
    def test_normal_2(self, client: TestClient, session: Session):
        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account["issuer"]
        coupontoken_1 = issue_coupon_token(issuer, {
            "name": "name_test1",
            "symbol": "symbol_test1",
            "totalSupply": 1000000,
            "tradableExchange": config.ZERO_ADDRESS,
            "details": "details_test1",
            "returnDetails": "returnDetails_test1",
            "memo": "memo_test1",
            "expirationDate": "20211201",
            "transferable": True,
            "contactInformation": "contactInformation_test1",
            "privacyPolicy": "privacyPolicy_test1"
        })
        coupon_register_list(issuer, coupontoken_1, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )
        user1 = eth_account["user1"]

        # NOTE: 残高なしの状態でクーポン消費
        tx = token_contract_1.functions.consume(10000).build_transaction({
            "from": to_checksum_address(user1["account_address"]),
            "gas": 6000000,
            "gasPrice": 0
        })
        tx_hash = web3.eth.send_transaction(tx)
        request_params = {
            "transaction_hash": tx_hash.hex()
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        with mock.patch("app.api.routers.eth.inspect_tx_failure", return_value="130401"):
            resp = client.post(
                self.apiurl,
                headers=headers,
                data=request_body
            )
            assert resp.status_code == 200
            assert resp.json()["meta"] == {
                'code': 200,
                'message': "OK"
            }
            assert resp.json()["data"] == {
                "status": 0, 
                "error_code": 130401, 
                "error_msg": "Message sender balance is insufficient."
            }

    ###################################################################
    # Error
    ###################################################################

    # Error_1
    # timeout設定なし（デフォルト採用）
    # -> 404エラー（Data not exists）
    def test_error_1(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )

        assert resp.status_code == 404
        assert resp.json()['meta'] == {
            'code': 30,
            'message': 'Data Not Exists'
        }

    # Error_2
    # timeout設定あり
    # -> 404エラー（Data not exists）
    def test_error_2(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 1
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )

        assert resp.status_code == 404
        assert resp.json()['meta'] == {
            'code': 30,
            'message': 'Data Not Exists'
        }

    # Error_3
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_error_3(self, client: TestClient, session: Session):
        resp = client.get(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()['meta'] == {
            'code': 1,
            'message': 'Method Not Allowed',
            'description': 'method: GET, url: /Eth/WaitForTransactionReceipt'
        }

    # Error_4
    # 入力値エラー（headers Content-Type不正）
    # -> 400エラー（InvalidParameterError）
    def test_error_4(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455"
        }
        headers: dict = {"Content-Type": "invalid type"}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 400
        assert resp.json()['meta'] == {
            'code': 88,
            'description': [
                {
                    'loc': ['body'],
                    'msg': 'value is not a valid dict',
                    'type': 'type_error.dict'
                }
            ],
            'message': 'Invalid Parameter'
        }

    # Error_5_1
    # 入力エラー（timeout最小値）
    # -> 400エラー
    def test_error_5_1(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 0
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"limit_value": 1},
                    "loc": ["body", "timeout"],
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_5_2
    # 入力エラー（timeout最大値）
    # -> 400エラー
    def test_error_5_2(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": 31
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"limit_value": 30},
                    "loc": ["body", "timeout"],
                    "msg": "ensure this value is less than or equal to 30",
                    "type": "value_error.number.not_le"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_6_1
    # 入力型エラー（transaction_hash）
    # -> 400エラー
    def test_error_6_1(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": 1234,
            "timeout": 1
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["body", "transaction_hash"],
                    "msg": "str type expected",
                    "type": "type_error.str"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_6_2
    # 入力型エラー（timeout）
    # -> 400エラー
    def test_error_6_2(self, client: TestClient, session: Session):
        request_params = {
            "transaction_hash": "0x01f4d994daef015cf4b3dbd750873c6de419de41a2063bd107812f06e0c2b455",
            "timeout": "aaaa"
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl,
            headers=headers,
            data=request_body
        )

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["body", "timeout"],
                    "msg": "value is not a valid integer",
                    "type": "type_error.integer"
                }
            ],
            "message": "Invalid Parameter"
        }
