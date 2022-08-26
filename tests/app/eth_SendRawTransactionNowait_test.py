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
from unittest.mock import patch

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
    coupon_register_list
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


# sendRawTransaction API (No Wait)
# /Eth/SendRawTransactionNoWait
class TestEthSendRawTransactionNoWait:

    # Test API
    apiurl = '/Eth/SendRawTransactionNoWait'

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Input list exists (1 entry)
    def test_normal_1(self, client: TestClient, session: Session):

        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account['issuer']
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

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(to_checksum_address(local_account_1.address), 10).buildTransaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000
            })
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json()['data']) == 1
        resp_data = resp.json()['data'][0]
        assert resp_data["id"] == 1
        assert resp_data["status"] == 1
        assert resp_data["transaction_hash"] is not None

    # <Normal_2>
    # Input list exists (multiple entries)
    def test_normal_2(self, client: TestClient, session: Session):

        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account['issuer']
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
        coupontoken_2 = issue_coupon_token(issuer, {
            "name": "name_test2",
            "symbol": "symbol_test2",
            "totalSupply": 1000000,
            "tradableExchange": config.ZERO_ADDRESS,
            "details": "details_test2",
            "returnDetails": "returnDetails_test2",
            "memo": "memo_test2",
            "expirationDate": "20211202",
            "transferable": True,
            "contactInformation": "contactInformation_test2",
            "privacyPolicy": "privacyPolicy_test2"
        })
        coupon_register_list(issuer, coupontoken_2, tokenlist)

        # Listing,実行可能コントラクト登録
        listing_token(session, coupontoken_1)
        executable_contract_token(session, coupontoken_1)
        listing_token(session, coupontoken_2)
        executable_contract_token(session, coupontoken_2)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_1.functions.transfer(to_checksum_address(local_account_1.address), 10).buildTransaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000
            })
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        token_contract_2 = web3.eth.contract(
            address=to_checksum_address(coupontoken_2["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_2 = web3.eth.account.create()

        # テスト用のトランザクション実行前の事前準備
        pre_tx = token_contract_2.functions.transfer(to_checksum_address(local_account_2.address), 10).buildTransaction(
            {
                "from": to_checksum_address(issuer["account_address"]),
                "gas": 6000000
            })
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        tx = token_contract_2.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_2.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_2.address))
        signed_tx_2 = web3.eth.account.sign_transaction(tx, local_account_2.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex(), signed_tx_2.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json()['data']) == 2
        resp_data = resp.json()['data'][0]
        assert resp_data["id"] == 1
        assert resp_data["status"] == 1
        assert resp_data["transaction_hash"] is not None
        resp_data = resp.json()['data'][1]
        assert resp_data["id"] == 2
        assert resp_data["status"] == 1
        assert resp_data["transaction_hash"] is not None

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Unsupported HTTP method
    # -> 404 Not Supported
    def test_error_1(self, client: TestClient, session: Session):
        resp = client.get(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()['meta'] == {
            'code': 1,
            'message': 'Method Not Allowed',
            'description': 'method: GET, url: /Eth/SendRawTransactionNoWait'
        }

    # <Error_2>
    # No headers
    # -> 400 InvalidParameterError
    def test_error_2(self, client: TestClient, session: Session):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 422
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                }
            ],
            "message": "Request Validation Error"
        }

    # <Error_3_1>
    # Input list is empty
    # -> 400 InvalidParameterError
    def test_error_3_1(self, client: TestClient, session: Session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS

        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 422
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "ctx": {"limit_value": 1},
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "ensure this value has at least 1 items",
                    "type": "value_error.list.min_items"
                }
            ],
            "message": "Request Validation Error"
        }

    # <Error_3_2>
    # No inputs
    # -> 400 InvalidParameterError
    def test_error_3_2(self, client: TestClient, session: Session):
        request_params = {}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 422
        assert resp.json()['meta'] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ],
            "message": "Request Validation Error"
        }

    # <Error_4>
    # Input values are incorrect (not a list)
    # -> 400 InvalidParameterError
    def test_error_4(self, client: TestClient, session: Session):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 422
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "raw_tx_hex_list"],
                    "msg": "value is not a valid list",
                    "type": "type_error.list"
                }
            ],
            "message": "Request Validation Error"
        }

    # <Error_5>
    # Input values are incorrect (not a string type)
    # -> 400 InvalidParameterError
    def test_error_5(self, client: TestClient, session: Session):
        raw_tx_1 = 1234
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 422
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["body", "raw_tx_hex_list", 0],
                    "msg": "str type expected",
                    "type": "type_error.str"
                }
            ],
            "message": "Request Validation Error"
        }

    # <Error_6>
    # Input values are incorrect (invalid transaction）
    # -> 200, status = 0
    def test_error_6(self, client: TestClient, session: Session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS

        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == [{'id': 1, 'status': 0}]

    # <Error_7>
    # Invalid token status
    def test_error_7(self, client: TestClient, session: Session):

        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account['issuer']
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

        # ステータス無効化
        pre_tx = token_contract_1.functions.setStatus(False).buildTransaction({
            "from": to_checksum_address(issuer["account_address"]),
            "gas": 6000000
        })
        tx_hash = web3.eth.send_transaction(pre_tx)
        web3.eth.wait_for_transaction_receipt(tx_hash)

        local_account_1 = web3.eth.account.create()

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 400
        assert resp.json()['meta'] == {
            'code': 20,
            'message': 'Suspended Token',
            'description': 'Token is currently suspended',
        }

    # <Error_8>
    # Non executable contract
    def test_error_8(self, client: TestClient, session: Session):

        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account['issuer']
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

        # Listing登録
        listing_token(session, coupontoken_1)

        token_contract_1 = web3.eth.contract(
            address=to_checksum_address(coupontoken_1["address"]),
            abi=coupontoken_1["abi"],
        )

        local_account_1 = web3.eth.account.create()

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.post(
            self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == [{
            "id": 1,
            "status": 0
        }]

    # <Error_9>
    # Transaction failed
    def test_error_9(self, client: TestClient, session: Session):

        # トークンリスト登録
        tokenlist = tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = tokenlist['address']
        issuer = eth_account['issuer']
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

        local_account_1 = web3.eth.account.create()

        # NOTE: ネットワークエラー
        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        with patch("web3.eth.Eth.send_raw_transaction", side_effect=ConnectionError):
            resp = client.post(
                self.apiurl, headers=headers, data=request_body)

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json()['data']) == 1
        resp_data = resp.json()['data'][0]
        assert resp_data["id"] == 1
        assert resp_data["status"] == 0
        assert resp_data["transaction_hash"] is None
