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
from web3.datastructures import AttributeDict
from web3.middleware import geth_poa_middleware
from web3.utils.threads import Timeout
from eth_utils import to_checksum_address
from unittest.mock import MagicMock
from unittest import mock

from app import config
from app.contracts import Contract
from app.model import Listing, ExecutableContract
from app.model.node import Node
from .account_config import eth_account
from .contract_modules import issue_coupon_token, coupon_register_list

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


def insert_node_data(session, is_synced):
    node = Node()
    node.is_synced = is_synced
    session.add(node)


def tokenlist_contract():
    issuer = eth_account['issuer']
    web3.eth.defaultAccount = issuer['account_address']
    web3.personal.unlockAccount(
        issuer['account_address'], issuer['password'])

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


class TestEthSendRawTransaction():
    # テスト対象API
    apiurl = '/v2/Eth/SendRawTransaction/'

    # ＜正常系1＞
    # 入力リストが空
    def test_sendraw_normal_1(self, client, session):
        insert_node_data(session, is_synced=True)

        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # ＜正常系2＞
    # 入力リストが1件
    def test_sendraw_normal_2(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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
        assert resp.json['data'] == [{
            "id": 1,
            "status": 1
        }]

    # ＜正常系2＞
    # 入力リストが1件
    def test_sendraw_normal_2(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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
        assert resp.json['data'] == [{
            "id": 1,
            "status": 1
        }]

    # ＜正常系3＞
    # 入力リストが複数件
    def test_sendraw_normal_3(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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
        assert resp.json['data'] == [{
            "id": 1,
            "status": 1
        }, {
            "id": 2,
            "status": 1
        }]

    # ＜正常系4＞
    # 入力リストが1件
    # トランザクション保留
    def test_sendraw_normal_4(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

        # タイムアウト
        # NOTE: GanacheにはRPCメソッド:txpool_inspectが存在しないためMock化
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=Timeout())), mock.patch(
                "web3.txpool.TxPool.inspect", AttributeDict({
                    "pending": AttributeDict({
                        to_checksum_address(local_account_1.address): AttributeDict({
                            str(tx["nonce"]): "0xffffffffffffffffffffffffffffffffffffffff: 0 wei + 999999 × 11111 gas"
                        })
                    }),
                    "queued": AttributeDict({})
                })):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 2
        }]

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_sendraw_error_1(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/SendRawTransaction'
        }

    # ＜エラー系2＞
    # headersなし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_2(self, client):
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

    # ＜エラー系3＞
    # 入力値なし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_3(self, client):
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

    # ＜エラー系4＞
    # 入力値が正しくない（リストではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_4(self, client):
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

    # ＜エラー系5＞
    # 入力値が正しくない（String型ではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_5(self, client):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
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

    # ＜エラー系6：ステータスコードは200＞
    # 入力値が正しくない（rawtransactionではない）
    # -> status = 0
    def test_sendraw_error_6(self, client, session):
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

    # ＜エラー系7＞
    # ブロック同期停止中
    def test_sendraw_error_7(self, client, session):
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

    # ＜エラー系8＞
    # 取扱ステータス無効
    def test_sendraw_error_8(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

    # ＜エラー系9＞
    # 実行可能コントラクト対象外
    def test_sendraw_error_9(self, client, session):
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

    # ＜エラー系10＞
    # トランザクション送信エラー
    def test_sendraw_error_10(self, client, session):
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
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # ＜エラー系11＞
    # トランザクション受付エラー
    def test_sendraw_error_11(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

        # waitForTransactionReceiptエラー
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=Exception())):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # ＜エラー系12＞
    # アドレス取得エラー
    def test_sendraw_error_12(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
        tx_hash = web3.eth.sendTransaction(pre_tx)
        web3.eth.waitForTransactionReceipt(tx_hash)

        tx = token_contract_1.functions.consume(10).buildTransaction({
            "from": to_checksum_address(local_account_1.address),
            "gas": 6000000
        })
        tx["nonce"] = web3.eth.getTransactionCount(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.signTransaction(tx, local_account_1.privateKey)

        # waitForTransactionReceiptエラー
        mock.patch.object(web3.eth, "waitForTransactionReceipt", MagicMock(side_effect=Timeout()))
        mock.patch.object(web3.eth.account, "recoverTransaction", MagicMock(side_effect=Exception()))

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # タイムアウト
        # recoverTransactionエラー
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=Timeout())), mock.patch(
                "eth_account.Account.recoverTransaction", MagicMock(side_effect=Exception())):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # ＜エラー系13＞
    # トランザクション受付タイムアウト、pending未昇格
    def test_sendraw_error_13(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

        # タイムアウト
        # queuedに滞留
        # NOTE: GanacheにはRPCメソッド:txpool_inspectが存在しないためMock化
        with mock.patch("web3.eth.Eth.waitForTransactionReceipt", MagicMock(side_effect=Timeout())), mock.patch(
                "web3.txpool.TxPool.inspect", AttributeDict({
                    "pending": AttributeDict({}),
                    "queued": AttributeDict({
                        to_checksum_address(local_account_1.address): AttributeDict({
                            str(tx["nonce"]): "0xffffffffffffffffffffffffffffffffffffffff: 0 wei + 999999 × 11111 gas"
                        })
                    })
                })):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]


# sendRawTransaction API (No Wait)
# /v2/Eth/SendRawTransactionNoWait
class TestEthSendRawTransactionNoWait():
    # テスト対象API
    apiurl = '/v2/Eth/SendRawTransactionNoWait/'

    # ＜正常系1＞
    # 入力リストが空
    def test_sendraw_normal_1(self, client, session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        insert_node_data(session, is_synced=True)

        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # ＜正常系2＞
    # 入力リストが1件
    def test_sendraw_normal_2(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

    # ＜正常系3＞
    # 入力リストが複数件
    def test_sendraw_normal_3(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_sendraw_error_1(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/SendRawTransactionNoWait'
        }

    # ＜エラー系2＞
    # headersなし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_2(self, client):
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

    # ＜エラー系3＞
    # 入力値なし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_3(self, client):
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

    # ＜エラー系4＞
    # 入力値が正しくない（リストではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_4(self, client):
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

    # ＜エラー系5＞
    # 入力値が正しくない（String型ではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_5(self, client):
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

    # ＜エラー系6：ステータスコードは200＞
    # 入力値が正しくない（rawtransactionではない）
    # -> status = 0
    def test_sendraw_error_6(self, client, session):
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

    # ＜エラー系7＞
    # ブロック同期停止中
    def test_sendraw_error_7(self, client, session):
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

    # ＜エラー系8＞
    # 取扱ステータス無効
    def test_sendraw_error_8(self, client, session):
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
        web3.personal.unlockAccount(to_checksum_address(issuer["account_address"]), issuer["password"], 60)
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

    # ＜エラー系9＞
    # 実行可能コントラクト対象外
    def test_sendraw_error_9(self, client, session):
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

    # ＜エラー系10＞
    # トランザクション送信エラー
    def test_sendraw_error_10(self, client, session):
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
