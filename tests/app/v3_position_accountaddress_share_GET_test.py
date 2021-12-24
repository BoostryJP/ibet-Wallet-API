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

from app import config
from app.model.db import Listing
from tests.account_config import eth_account
from tests.utils import (
    PersonalInfoUtils,
    IbetShareUtils
)


class TestPositionAccountAddressShare:
    # Test API
    apiurl = "/v3/Position/{account_address}/Share"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]
    zero_address = {"address": config.ZERO_ADDRESS}

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account,
                            exchange_contract,
                            personal_info_contract,
                            token_list_contract):
        issuer_address = TestPositionAccountAddressShare.issuer["account_address"]

        # Issue token
        args = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_contract["address"],
            "personalInfoAddress": personal_info_contract["address"],
            "issuePrice": 1000,
            "principalValue": 1000,
            "totalSupply": 1000000,
            "dividends": 101,
            "dividendRecordDate": "20200401",
            "dividendPaymentDate": "20200502",
            "cancellationDate": "20200603",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "memo": "メモ",
            "transferable": True
        }
        token = IbetShareUtils.issue(
            tx_from=issuer_address,
            args=args
        )
        IbetShareUtils.register_token_list(
            tx_from=issuer_address,
            token_address=token.address,
            token_list_contract_address=token_list_contract["address"]
        )
        PersonalInfoUtils.register(
            tx_from=account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address
        )
        IbetShareUtils.transfer_to_exchange(
            tx_from=issuer_address,
            exchange_address=account["account_address"],
            token_address=token.address,
            amount=1000000
        )

        return token

    # Prepare pending_transfer data
    # balance = 1000000, pending_transfer = [args pending_transfer]
    @staticmethod
    def create_pending_transfer_data(account,
                                     to_account,
                                     exchange_contract,
                                     personal_info_contract,
                                     token_list_contract,
                                     pending_transfer):
        issuer_address = TestPositionAccountAddressShare.issuer["account_address"]

        # Issue token
        token = TestPositionAccountAddressShare.create_balance_data(
            account,
            exchange_contract,
            personal_info_contract,
            token_list_contract
        )

        # Apply for transfer
        IbetShareUtils.set_transfer_approval_required(
            tx_from=issuer_address,
            token_address=token.address,
            required=True
        )
        PersonalInfoUtils.register(
            tx_from=to_account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address
        )
        IbetShareUtils.apply_for_transfer(
            tx_from=account["account_address"],
            token_address=token.address,
            to=to_account["account_address"],
            value=pending_transfer
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(account, exchange_contract, personal_info_contract, token_list_contract, commitment):
        # Issue token
        token = TestPositionAccountAddressShare.create_balance_data(
            account,
            exchange_contract,
            personal_info_contract,
            token_list_contract
        )

        # Sell order
        IbetShareUtils.sell(
            tx_from=account["account_address"],
            exchange_address=exchange_contract["address"],
            token_address=token.address,
            amount=commitment,
            price=1000
        )

        return token

    # Prepare non balance data
    # balance = 0
    @staticmethod
    def create_non_balance_data(account, to_account, exchange_contract,
                                personal_info_contract, token_list_contract):
        issuer_address = TestPositionAccountAddressShare.issuer["account_address"]

        # Issue token
        token = TestPositionAccountAddressShare.create_balance_data(
            account,
            exchange_contract,
            personal_info_contract,
            token_list_contract
        )

        # Transfer all amount
        PersonalInfoUtils.register(
            tx_from=to_account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address
        )
        IbetShareUtils.transfer_to_exchange(
            tx_from=account["account_address"],
            exchange_address=to_account["account_address"],
            token_address=token.address,
            amount=1000000
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
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract)
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_1.address, session)

        token_2 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_2.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_3 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            100
        )
        self.list_token(token_3.address, session)

        token_4 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            1000000
        )
        self.list_token(token_4.address, session)

        token_5 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100
        )
        self.list_token(token_5.address, session)

        token_6 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000
        )
        self.list_token(token_6.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            # Request target API
            resp = client.simulate_get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
            )

        assert resp.status_code == 200
        assert resp.json["data"] == {
            "result_set": {
                "count": 6,
                "offset": None,
                "limit": None,
                "total": 6,
            },
            "positions": [
                {
                    "token_address": token_1.address,
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_2.address,
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_3.address,
                    "balance": 999900,
                    "pending_transfer": 100,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_4.address,
                    "balance": 0,
                    "pending_transfer": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_5.address,
                    "balance": 999900,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                },
                {
                    "token_address": token_6.address,
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
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_1.address, session)

        token_2 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_2.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_3 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            100
        )
        self.list_token(token_3.address, session)

        token_4 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            1000000
        )
        self.list_token(token_4.address, session)

        token_5 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100
        )
        self.list_token(token_5.address, session)

        token_6 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000
        )
        self.list_token(token_6.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract
        )
        self.list_token(token_non.address, session)  # not target

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
                "count": 6,
                "offset": 1,
                "limit": 2,
                "total": 6,
            },
            "positions": [
                {
                    "token_address": token_2.address,
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                },
                {
                    "token_address": token_3.address,
                    "balance": 999900,
                    "pending_transfer": 100,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
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
        router_obj = client.app._router_search("/v3/Position/{account_address}/Share")[0]
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
            "description": f"method: GET, url: /v3/Position/{account_address}/Share"
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
