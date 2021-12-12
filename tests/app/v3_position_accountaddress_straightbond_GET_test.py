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
from tests.utils import PersonalInfoUtils
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    bond_transfer_to_exchange
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionAccountAddressStraightBond:
    # Test API
    apiurl = "/v3/Position/{account_address}/StraightBond"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account, exchange_contract,
                            personal_info_contract, token_list_contract):
        issuer_address = TestPositionAccountAddressStraightBond.issuer["account_address"]

        # Issue token
        args = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange_contract['address'],
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
            'personalInfoAddress': personal_info_contract['address'],
            'transferable': True,
            'isRedeemed': False
        }
        token = issue_bond_token(TestPositionAccountAddressStraightBond.issuer, args)
        register_bond_list(TestPositionAccountAddressStraightBond.issuer, token, token_list_contract)
        PersonalInfoUtils.register(
            tx_from=account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address
        )
        bond_transfer_to_exchange(
            TestPositionAccountAddressStraightBond.issuer,
            {"address": account["account_address"]},
            token,
            1000000
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(account, exchange_contract, personal_info_contract, token_list_contract, commitment):
        # Issue token
        token = TestPositionAccountAddressStraightBond.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract)

        # Sell order
        agent = eth_account["agent"]
        bond_transfer_to_exchange(
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
    def create_non_balance_data(account, to_account, exchange_contract,
                                personal_info_contract, token_list_contract):
        issuer_address = TestPositionAccountAddressStraightBond.issuer["account_address"]

        # Issue token
        token = TestPositionAccountAddressStraightBond.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract)

        # Transfer all amount
        PersonalInfoUtils.register(
            tx_from=to_account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address
        )
        bond_transfer_to_exchange(
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
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, personal_info_contract, token_list_contract)
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, personal_info_contract, token_list_contract)
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1, exchange_contract, personal_info_contract, token_list_contract, 100)
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1, exchange_contract, personal_info_contract, token_list_contract, 1000000)
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
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
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                },
                {
                    "token_address": token_4["address"],
                    "balance": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                },
            ]
        }

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, personal_info_contract, token_list_contract)
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, personal_info_contract, token_list_contract)
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1, exchange_contract, personal_info_contract, token_list_contract, 100)
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1, exchange_contract, personal_info_contract, token_list_contract, 1000000)
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, personal_info_contract,
            token_list_contract)
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
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "pending_transfer": 0,
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
        router_obj = client.app._router_search("/v3/Position/{account_address}/StraightBond")[0]
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
            "description": f"method: GET, url: /v3/Position/{account_address}/StraightBond"
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
