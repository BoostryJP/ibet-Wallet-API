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
from unittest import mock

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model import (
    Listing,
    IDXTransfer
)
from app.tests.account_config import eth_account
from .contract_modules import (
    issue_coupon_token,
    coupon_register_list,
    transfer_coupon_token,
    consume_coupon_token
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionAccountAddressCoupon:
    # Test API
    apiurl = "/v3/Position/{account_address}/Coupon"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account, exchange_contract, token_list_contract):

        # Issue token
        args = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
            'tradableExchange': exchange_contract['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }
        token = issue_coupon_token(TestPositionAccountAddressCoupon.issuer, args)
        coupon_register_list(TestPositionAccountAddressCoupon.issuer, token, token_list_contract)
        transfer_coupon_token(
            TestPositionAccountAddressCoupon.issuer,
            token,
            account["account_address"],
            1000000
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(account, exchange_contract, token_list_contract, commitment):
        # Issue token
        token = TestPositionAccountAddressCoupon.create_balance_data(
            account, exchange_contract, token_list_contract)

        # Sell order
        agent = eth_account["agent"]
        transfer_coupon_token(
            account,
            token,
            exchange_contract["address"],
            commitment
        )
        ExchangeContract = Contract.get_contract(
            'IbetExchange', exchange_contract['address'])
        tx_hash = ExchangeContract.functions. \
            createOrder(token['address'], commitment, 10000, False, agent['account_address']). \
            transact({'from': account['account_address'], 'gas': 4000000})
        web3.eth.waitForTransactionReceipt(tx_hash)

        return token

    # Prepare used data
    # balance = 1000000 - commitment, used = [args used]
    @staticmethod
    def create_used_data(account, exchange_contract, token_list_contract, used):
        # Issue token
        token = TestPositionAccountAddressCoupon.create_balance_data(
            account, exchange_contract, token_list_contract)

        # Used
        consume_coupon_token(account, token, used)

        return token

    # Prepare non balance data
    # balance = 0
    @staticmethod
    def create_non_balance_data(account, to_account, exchange_contract, token_list_contract):

        # Issue token
        token = TestPositionAccountAddressCoupon.create_balance_data(
            account, exchange_contract, token_list_contract)

        # Transfer all amount
        transfer_coupon_token(
            account,
            token,
            to_account["account_address"],
            1000000
        )

        return token

    @staticmethod
    def list_token(token_address, session):
        listed_token = Listing()
        listed_token.token_address = token_address
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    ###########################################################################
    # Normal
    ###########################################################################

    # <Normal_1>
    # List all positions
    def test_normal_1(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(self.account_1, exchange_contract, token_list_contract, 100)
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(self.account_1, exchange_contract, token_list_contract, 1000000)
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_5 = self.create_used_data(self.account_1, exchange_contract, token_list_contract, 100)
        self.list_token(token_5["address"], session)
        token_6 = self.create_used_data(self.account_1, exchange_contract, token_list_contract, 1000000)
        self.list_token(token_6["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_7 = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_7["address"], session)
        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7["address"]
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        session.add(idx_transfer)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            # Request target API
            resp = client.simulate_get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
            )

        assert resp.status_code == 200
        assert resp.json["data"] == {
            "result_set": {
                "count": 7,
                "offset": None,
                "limit": None,
                "total": 7,
            },
            "positions": [
                {
                    "token_address": token_1["address"],
                    "balance": 1000000,
                    "commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "commitment": 100,
                    "used": 0,
                },
                {
                    "token_address": token_4["address"],
                    "balance": 0,
                    "commitment": 1000000,
                    "used": 0,
                },
                {
                    "token_address": token_5["address"],
                    "balance": 999900,
                    "commitment": 0,
                    "used": 100,
                },
                {
                    "token_address": token_6["address"],
                    "balance": 0,
                    "commitment": 0,
                    "used": 1000000,
                },
                {
                    "token_address": token_7["address"],
                    "balance": 0,
                    "commitment": 0,
                    "used": 0,
                },
            ]
        }

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(self.account_1, exchange_contract, token_list_contract, 100)
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(self.account_1, exchange_contract, token_list_contract, 1000000)
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_5 = self.create_used_data(self.account_1, exchange_contract, token_list_contract, 100)
        self.list_token(token_5["address"], session)
        token_6 = self.create_used_data(self.account_1, exchange_contract, token_list_contract, 1000000)
        self.list_token(token_6["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_7 = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_7["address"], session)
        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7["address"]
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        session.add(idx_transfer)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            # Request target API
            resp = client.simulate_get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={
                    "offset": 1,
                    "limit": 2,
                }
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["data"] == {
            "result_set": {
                "count": 7,
                "offset": 1,
                "limit": 2,
                "total": 7,
            },
            "positions": [
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "commitment": 100,
                    "used": 0,
                },
            ]
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client, session):

        account_address = self.account_1["account_address"]

        # Request target API
        router_obj = client.app._router_search("/v3/Position/{account_address}/Coupon")[0]
        origin_data = router_obj.token_enabled
        try:
            router_obj.token_enabled = False
            resp = client.simulate_get(
                self.apiurl.format(account_address=account_address),
            )
        finally:
            router_obj.token_enabled = origin_data

        # Assertion
        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": f"method: GET, url: /v3/Position/{account_address}/Coupon"
        }

    # <Error_2>
    # ParameterError: invalid account_address
    def test_error_2(self, client, session):

        # Request target API
        resp = client.simulate_get(
            self.apiurl.format(account_address="invalid"),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid account_address"
        }

    # <Error_3>
    # ParameterError: offset/limit(minus value)
    def test_error_3(self, client, session):

        # Request target API
        resp = client.simulate_get(
            self.apiurl.format(account_address=self.account_1["account_address"]),
            params={
                "offset": -1,
                "limit": -1,
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "offset": "min value is 0",
                "limit": "min value is 0",
            }
        }

    # <Error_4>
    # ParameterError: offset/limit(not int)
    def test_error_4(self, client, session):

        # Request target API
        resp = client.simulate_get(
            self.apiurl.format(account_address=self.account_1["account_address"]),
            params={
                "offset": "test",
                "limit": "test",
            }
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "offset": ["field 'offset' could not be coerced", "must be of integer type"],
                "limit": ["field 'limit' could not be coerced", "must be of integer type"],
            }
        }
