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
from unittest.mock import MagicMock
from unittest import mock

from web3 import Web3
from web3.datastructures import AttributeDict
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted, ContractLogicError
from eth_utils import to_checksum_address

from app import config
from app.api.v2 import eth
from app.contracts import Contract
from app.model.db import (
    Listing,
    ExecutableContract,
    Node
)

from tests.account_config import eth_account
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


def insert_node_data(session, is_synced, endpoint_uri=config.WEB3_HTTP_PROVIDER, priority=0):
    node = Node()
    node.is_synced = is_synced
    node.endpoint_uri = endpoint_uri
    node.priority = priority
    session.add(node)
    session.commit()


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


class TestEthSendRawTransaction:
    # Test API
    apiurl = '/v2/Eth/SendRawTransaction/'

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # Input list exists (1 entry)
    # Web3 FailOver
    def test_normal_1(self, client, session):
        with mock.patch("app.utils.web3_utils.FailOverHTTPProvider.fail_over_mode", True):
            insert_node_data(session, is_synced=False, endpoint_uri="http://localhost:8546")
            insert_node_data(session, is_synced=True, endpoint_uri=config.WEB3_HTTP_PROVIDER, priority=1)

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

            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

            assert resp.status_code == 200
            assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
            assert resp.json['data'] == [{
                "id": 1,
                "status": 1
            }]

    # <Normal_2>
    # Input list exists (multiple entries)
    def test_normal_2(self, client, session):

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

    # <Normal_3>
    # pending transaction
    def test_normal_3(self, client, session):

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

        # タイムアウト
        # NOTE: GanacheにはRPCメソッド:txpool_inspectが存在しないためMock化
        with mock.patch("web3.eth.Eth.wait_for_transaction_receipt", MagicMock(side_effect=TimeExhausted())), mock.patch(
                "web3.geth.GethTxPool.inspect", MagicMock(side_effect=[AttributeDict({
                    "pending": AttributeDict({
                        to_checksum_address(local_account_1.address): AttributeDict({
                            str(tx["nonce"]): "0xffffffffffffffffffffffffffffffffffffffff: 0 wei + 999999 × 11111 gas"
                        })
                    }),
                    "queued": AttributeDict({})
                })])):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 2
        }]

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # Unsupported HTTP method
    # -> 404 Not Supported
    def test_error_1(self, client, session):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Eth/SendRawTransaction'
        }

    # <Error_2>
    # No headers
    # -> 400 InvalidParameterError
    def test_error_2(self, client, session):
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

    # <Error_3_1>
    # Input list is empty
    # -> 400 InvalidParameterError
    def test_error_3_1(self, client, session):

        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS
        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': ['empty values not allowed']
            }
        }

    # <Error_3_2>
    # No inputs
    # -> 400 InvalidParameterError
    def test_error_3_2(self, client, session):
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
                'raw_tx_hex_list': ['required field']
            }
        }

    # <Error_4>
    # Input values are incorrect (not a list type)
    # -> 400 InvalidParameterError
    def test_error_4(self, client, session):
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
                'raw_tx_hex_list': ['must be of list type']
            }
        }

    # <Error_5>
    # Input values are incorrect (not a string type)
    # -> 400 InvalidParameterError
    def test_error_5(self, client, session):
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
                'raw_tx_hex_list': [
                    {
                        '0': ['must be of string type']
                    }
                ]
            }
        }

    # <Error_6>
    # Input values are incorrect (invalid transaction）
    # -> 200, status = 0
    def test_error_6(self, client, session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS

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
    # block synchronization stop(Web3 FailOver Error)
    def test_error_7(self, client, session):
        config.TOKEN_LIST_CONTRACT_ADDRESS = config.ZERO_ADDRESS

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
        with mock.patch("app.utils.web3_utils.FailOverHTTPProvider.fail_over_mode", True):
            insert_node_data(session, is_synced=False)
            insert_node_data(session, is_synced=False, endpoint_uri="http://localhost:8546", priority=1)
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

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # <Error_10_1>
    # Transaction failed and revert inspection success
    def test_error_10_1(self, client, session):

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
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert 130401',...})
        #         geth: ContractLogicError("execution reverted: 130401")
        #       Transactionリプレイが行われる5回目のcallのみ、GethのrevertによるExceptionを再現するようMock化
        eth_call_mock = MagicMock()
        successor = iter([True, True, True, True])

        def side_effect(*arg, **kwargs):
            global web3
            try:
                if next(successor):
                    return web3.eth.call(*arg, **kwargs)
            except Exception as e:
                raise ContractLogicError("execution reverted: 130401")

        eth_call_mock.side_effect = side_effect
        with mock.patch.object(eth.web3.eth, "call", eth_call_mock):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

            assert resp.status_code == 200
            assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
            assert resp.json['data'] == [{
                "id": 1,
                "status": 0,
                "error_code": 130401,
                "error_msg": "Message sender balance is insufficient.",
            }]

    # <Error_10_2>
    # Transaction failed and revert inspection success(no error code)
    def test_error_10_2(self, client, session):

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
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert Direct...',...})
        #         geth: ContractLogicError("execution reverted: Direct transfer is...")
        #       Transactionリプレイが行われる5回目のcallのみ、GethのrevertによるExceptionを再現するようMock化
        eth_call_mock = MagicMock()
        successor = iter([True, True, True, True])

        def side_effect(*arg, **kwargs):
            global web3
            try:
                if next(successor):
                    return web3.eth.call(*arg, **kwargs)
            except Exception as e:
                raise ContractLogicError("execution reverted: Message sender balance is insufficient.")

        eth_call_mock.side_effect = side_effect
        with mock.patch.object(eth.web3.eth, "call", eth_call_mock):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

            assert resp.status_code == 200
            assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
            assert resp.json['data'] == [{
                "id": 1,
                "status": 0,
                "error_code": 0,
                "error_msg": "Message sender balance is insufficient.",
            }]

    # <Error_10_3>
    # Transaction failed and revert inspection success(no revert message)
    def test_error_10_3(self, client, session):

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
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # NOTE: Ganacheがrevertする際にweb3.pyからraiseされるExceptionはGethと異なる
        #         ganache: ValueError({'message': 'VM Exception while processing transaction: revert',...})
        #         geth: ContractLogicError("execution reverted")
        #       Transactionリプレイが行われる5回目のcallのみ、GethのrevertによるExceptionを再現するようMock化
        eth_call_mock = MagicMock()
        successor = iter([True, True, True, True])

        def side_effect(*arg, **kwargs):
            global web3
            try:
                if next(successor):
                    return web3.eth.call(*arg, **kwargs)
            except Exception as e:
                raise ContractLogicError("execution reverted")

        eth_call_mock.side_effect = side_effect
        with mock.patch.object(eth.web3.eth, "call", eth_call_mock):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

            assert resp.status_code == 200
            assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
            assert resp.json['data'] == [{
                "id": 1,
                "status": 0,
                "error_code": 0,
                "error_msg": "execution reverted",
            }]

    # <Error_10_4>
    # Transaction failed and revert inspection failed
    def test_error_10_4(self, client, session):

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
        tx["nonce"] = web3.eth.get_transaction_count(to_checksum_address(local_account_1.address))
        signed_tx_1 = web3.eth.account.sign_transaction(tx, local_account_1.privateKey)

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        with mock.patch.object(eth.web3.eth, "getTransaction", ConnectionError):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

            assert resp.status_code == 200
            assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
            assert resp.json['data'] == [{
                "id": 1,
                "status": 0
            }]

    # <Error_11>
    # waitForTransactionReceipt error
    def test_error_11(self, client, session):

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

        # waitForTransactionReceiptエラー
        with mock.patch("web3.eth.Eth.wait_for_transaction_receipt", MagicMock(side_effect=Exception())):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # <Error_12>
    # recoverTransaction error
    def test_error_12(self, client, session):

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

        # waitForTransactionReceiptエラー
        mock.patch.object(web3.eth, "waitForTransactionReceipt", MagicMock(side_effect=TimeExhausted()))
        mock.patch.object(web3.eth.account, "recoverTransaction", MagicMock(side_effect=Exception()))

        request_params = {"raw_tx_hex_list": [signed_tx_1.rawTransaction.hex()]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # タイムアウト
        # recoverTransactionエラー
        with mock.patch("web3.eth.Eth.wait_for_transaction_receipt", MagicMock(side_effect=TimeExhausted())), mock.patch(
                "eth_account.Account.recoverTransaction", MagicMock(side_effect=Exception())):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]

    # <Error_13>
    # Transaction timeout, no transition to pending
    def test_error_13(self, client, session):

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

        # タイムアウト
        # queuedに滞留
        # NOTE: GanacheにはRPCメソッド:txpool_inspectが存在しないためMock化
        with mock.patch("web3.eth.Eth.wait_for_transaction_receipt", MagicMock(side_effect=TimeExhausted())), mock.patch(
                "web3.geth.GethTxPool.inspect", MagicMock(side_effect=[AttributeDict({
                    "pending": AttributeDict({}),
                    "queued": AttributeDict({
                        to_checksum_address(local_account_1.address): AttributeDict({
                            str(tx["nonce"]): "0xffffffffffffffffffffffffffffffffffffffff: 0 wei + 999999 × 11111 gas"
                        })
                    })
                })])):
            resp = client.simulate_post(
                self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == [{
            "id": 1,
            "status": 0
        }]
