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

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import config
from app.contracts import Contract
from app.model import (
    Listing,
    ExecutableContract
)
from app.model.node import Node

from tests.account_config import eth_account
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def insert_node_data(session, is_synced):
    node = Node()
    node.is_synced = is_synced
    session.add(node)


def tokenlist_contract():
    issuer = eth_account['issuer']
    web3.eth.defaultAccount = issuer['account_address']
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
# /v2/Eth/SendRawTransactionNoWait
class TestEthSendRawTransactionNoWait:

    # Test API
    apiurl = '/v2/Eth/SendRawTransactionNoWait/'

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Input list is empty
    def test_normal_1(self, client, session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        insert_node_data(session, is_synced=True)

        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # <Normal_2>
    # Input list exists (1 entry)
    def test_normal_2(self, client, session):
        insert_node_data(session, is_synced=True)

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
        tx_hash = web3.eth.sendTransaction(pre_tx)
        web3.eth.waitForTransactionReceipt(tx_hash)

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.signTransaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json['data']) == 1
        resp_data = resp.json['data'][0]
        assert resp_data["id"] == 1
        assert resp_data["status"] == 1
        assert resp_data["transaction_hash"] is not None

    # <Normal_3>
    # Input list exists (multiple entries)
    def test_normal_3(self, client, session):
        insert_node_data(session, is_synced=True)

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
        tx_hash = web3.eth.sendTransaction(pre_tx)
        web3.eth.waitForTransactionReceipt(tx_hash)

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.signTransaction(tx, local_account_1.privateKey)

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
        tx_hash = web3.eth.sendTransaction(pre_tx)
        web3.eth.waitForTransactionReceipt(tx_hash)

        tx = token_contract_2.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_2.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_2.address))
        signed_tx_2 = web3.eth.account.signTransaction(tx, local_account_2.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex(), signed_tx_2.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json['data']) == 2
        resp_data = resp.json['data'][0]
        assert resp_data["id"] == 1
        assert resp_data["status"] == 1
        assert resp_data["transaction_hash"] is not None
        resp_data = resp.json['data'][1]
        assert resp_data["id"] == 2
        assert resp_data["status"] == 1
        assert resp_data["transaction_hash"] is not None

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Unsupported HTTP method
    # -> 404 Not Supported
    def test_error_1(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/SendRawTransactionNoWait'
        }

    # <Error_2>
    # No headers
    # -> 400 InvalidParameterError
    def test_error_2(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # <Error_3>
    # No inputs
    # -> 400 InvalidParameterError
    def test_error_3(self, client):
        request_params = {}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'required field'
            }
        }

    # <Error_4>
    # Input values are incorrect (not a list)
    # -> 400 InvalidParameterError
    def test_error_4(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'must be of list type'
            }
        }

    # <Error_5>
    # Input values are incorrect (not a string type)
    # -> 400 InvalidParameterError
    def test_error_5(self, client):
        raw_tx_1 = 1234
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # <Error_6>
    # Input values are incorrect (invalid transaction）
    # -> 200, status = 0
    def test_error_6(self, client, session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        insert_node_data(session, is_synced=True)

        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{'id': 1, 'status': 0}]

    # <Error_7>
    # block synchronization stop
    def test_error_7(self, client, session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        insert_node_data(session, is_synced=False)

        raw_tx_1 = 'raw_tx_1'
        request_params = {'raw_tx_hex_list': [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)
        assert resp.status_code == 503
        assert resp.json['meta'] == {
            'code': 503,
            'message': 'Service Unavailable',
            'description': 'Block synchronization is down',
        }

    # <Error_8>
    # Invalid token status
    def test_error_8(self, client, session):
        insert_node_data(session, is_synced=True)

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
        tx_hash = web3.eth.sendTransaction(pre_tx)
        web3.eth.waitForTransactionReceipt(tx_hash)

        local_account_1 = web3.eth.account.create()

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.signTransaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 20,
            'message': 'Suspended Token',
            'description': 'Token is currently suspended',
        }

    # <Error_9>
    # Non executable contract
    def test_error_9(self, client, session):
        insert_node_data(session, is_synced=True)

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
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.signTransaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # <Error_10>
    # Transaction failed
    def test_error_10(self, client, session):
        insert_node_data(session, is_synced=True)

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

        # NOTE: 残高なしの状態でクーポン消費
        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.signTransaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json['data']) == 1
        resp_data = resp.json['data'][0]
        assert resp_data["id"] == 1
        assert resp_data["status"] == 0
        assert resp_data["transaction_hash"] is None
