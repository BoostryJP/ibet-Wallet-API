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
from app.model.db import Listing
from tests.account_config import eth_account
from tests.contract_modules import (
    membership_issue,
    membership_register_list,
    membership_transfer_to_exchange
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionAccountAddressMembership:
    # Test API
    apiurl = "/v3/Position/{account_address}/Membership"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account, exchange_contract, token_list_contract):

        # Issue token
        args = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange_contract['address'],
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }
        token = membership_issue(TestPositionAccountAddressMembership.issuer, args)
        membership_register_list(TestPositionAccountAddressMembership.issuer, token, token_list_contract)
        membership_transfer_to_exchange(
            TestPositionAccountAddressMembership.issuer,
            {"address": account["account_address"]},
            token,
            1000000
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(account, exchange_contract, token_list_contract, commitment):
        # Issue token
        token = TestPositionAccountAddressMembership.create_balance_data(
            account, exchange_contract, token_list_contract)

        # Sell order
        agent = eth_account["agent"]
        membership_transfer_to_exchange(
            account,
            exchange_contract,
            token,
            commitment
        )
        ExchangeContract = Contract.get_contract(
            'IbetExchange', exchange_contract['address'])
        tx_hash = ExchangeContract.functions. \
            createOrder(token['address'], commitment, 10000, False, agent['account_address']). \
            transact({'from': account['account_address'], 'gas': 4000000})
        web3.eth.waitForTransactionReceipt(tx_hash)

        return token

    # Prepare non balance data
    # balance = 0
    @staticmethod
    def create_non_balance_data(account, to_account, exchange_contract, token_list_contract):

        # Issue token
        token = TestPositionAccountAddressMembership.create_balance_data(
            account, exchange_contract, token_list_contract)

        # Transfer all amount
        membership_transfer_to_exchange(
            account,
            {"address": to_account["account_address"]},
            token,
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
        exchange_contract = shared_contract["IbetMembershipExchange"]
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

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            # Request target API
            resp = client.simulate_get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
            )

        assert resp.status_code == 200
        assert resp.json["data"] == {
            "result_set": {
                "count": 4,
                "offset": None,
                "limit": None,
                "total": 4,
            },
            "positions": [
                {
                    "token_address": token_1["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                },
                {
                    "token_address": token_4["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                },
            ]
        }

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetMembershipExchange"]
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
                "count": 4,
                "offset": 1,
                "limit": 2,
                "total": 4,
            },
            "positions": [
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
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
        router_obj = client.app._router_search("/v3/Position/{account_address}/Membership")[0]
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
            "description": f"method: GET, url: /v3/Position/{account_address}/Membership"
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
                "offset": ["min value is 0"],
                "limit": ["min value is 0"],
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
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' cannot be coerced: invalid literal for int() with base 10: 'test'",
                    'must be of integer type'
                ],
                'offset': [
                    "field 'offset' cannot be coerced: invalid literal for int() with base 10: 'test'",
                    'must be of integer type'
                ]
            }
        }
