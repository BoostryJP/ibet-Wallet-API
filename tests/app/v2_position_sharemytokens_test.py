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

from app import config
from app.model import Listing
from tests.account_config import eth_account
from tests.utils import (
    PersonalInfoUtils,
    IbetShareUtils
)


class TestV2ShareMyTokens:
    """
    Test Case for v2.position.ShareMyTokens
    """

    # Target API endpoint
    apiurl = "/v2/Position/Share"

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account, exchange_contract,
                            personal_info_contract, token_list_contract):
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
            tx_from=account["account_address"],
            args=args
        )
        IbetShareUtils.register_token_list(
            tx_from=account["account_address"],
            token_address=token["address"],
            token_list_contract_address=token_list_contract["address"]
        )
        return token

    # Prepare pending_transfer data
    # balance = 999900, pending_transfer = 100
    @staticmethod
    def create_pending_transfer_data(account, exchange_contract,
                                     personal_info_contract, token_list_contract):
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
            tx_from=account["account_address"],
            args=args
        )
        IbetShareUtils.register_token_list(
            tx_from=account["account_address"],
            token_address=token["address"],
            token_list_contract_address=token_list_contract["address"]
        )
        # Apply for transfer
        IbetShareUtils.set_transfer_approval_required(
            tx_from=account["account_address"],
            token_address=token["address"],
            required=True
        )
        IbetShareUtils.apply_for_transfer(
            tx_from=account["account_address"],
            token_address=token["address"],
            to=account["account_address"],
            value=100
        )
        return token

    # Prepare commitment data
    # balance = 999900, commitment = 100
    @staticmethod
    def create_commitment_data(account, exchange_contract, personal_info_contract, token_list_contract):
        PersonalInfoUtils.register(
            tx_from=account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=account["account_address"]
        )
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
            tx_from=account["account_address"],
            args=args
        )
        IbetShareUtils.register_token_list(
            tx_from=account["account_address"],
            token_address=token["address"],
            token_list_contract_address=token_list_contract["address"]
        )
        # Sell order
        IbetShareUtils.sell(
            tx_from=account["account_address"],
            exchange_address=exchange_contract["address"],
            token_address=token["address"],
            amount=100,
            price=1000
        )
        return token

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token["address"]
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # balance > 0, pending_transfer = 0, exchange_balance = 0
    def test_normal_1(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        issuer = eth_account["issuer"]

        # Prepare data
        token = self.create_balance_data(
            account=issuer,
            exchange_contract=exchange_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        token_address = token["address"]
        self.list_token(session, token)
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange_contract["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Request target API
        request_params = {
            "account_address_list": [
                issuer["account_address"]
            ]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assumed_body = {
            "token": {
                "token_address": token_address,
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "balance": 1000000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}

        count = 0
        for token in resp.json["data"]:
            if token["token"]["token_address"] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # Normal_2
    # balance > 0, pending_transfer > 0, exchange_balance = 0
    def test_normal_2(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        issuer = eth_account["issuer"]

        # Prepare data
        token = self.create_pending_transfer_data(
            account=issuer,
            exchange_contract=exchange_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        token_address = token["address"]
        self.list_token(session, token)
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange_contract["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Request target API
        request_params = {
            "account_address_list": [
                issuer["account_address"]
            ]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assumed_body = {
            "token": {
                "token_address": token_address,
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": True,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },

            "balance": 999900,
            "pending_transfer": 100,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }
        count = 0
        for token in resp.json["data"]:
            if token["token"]["token_address"] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # Normal_3
    # balance > 0, pending_transfer = 0, exchange_balance > 0
    def test_normal_3(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        issuer = eth_account["issuer"]

        # Prepare data
        token = self.create_commitment_data(
            account=issuer,
            exchange_contract=exchange_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        token_address = token["address"]
        self.list_token(session, token)
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange_contract["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Request target API
        request_params = {
            "account_address_list": [
                issuer["account_address"]
            ]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assumed_body = {
            "token": {
                "token_address": token_address,
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },

            "balance": 999900,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 100,
        }
        count = 0
        for token in resp.json["data"]:
            if token["token"]["token_address"] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # Normal_4
    # balance > 0, exchange_balance > 0
    # Exchange address not set
    def test_normal_4(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        issuer = eth_account["issuer"]

        # Prepare data
        token = self.create_commitment_data(
            account=issuer,
            exchange_contract=exchange_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        token_address = token["address"]
        self.list_token(session, token)
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None  # Exchange address not set
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Request target API
        request_params = {
            "account_address_list": [
                issuer["account_address"]
            ]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assumed_body = {
            "token": {
                "token_address": token_address,
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "balance": 999900,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }
        count = 0
        for token in resp.json["data"]:
            if token["token"]["token_address"] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # Normal_5
    # Multiple record
    def test_normal_5(self, client, session, shared_contract):
        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        issuer = eth_account["issuer"]

        # Prepare data (1)
        token_1 = self.create_balance_data(
            account=issuer,
            exchange_contract=exchange_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        token_address_1 = token_1["address"]
        self.list_token(session, token_1)

        # Prepare data (2)
        token_2 = self.create_balance_data(
            account=issuer,
            exchange_contract=exchange_contract,
            personal_info_contract=personal_info_contract,
            token_list_contract=token_list_contract
        )
        token_address_2 = token_2["address"]
        self.list_token(session, token_2)

        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange_contract["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]

        # Request target API
        request_params = {
            "account_address_list": [
                issuer["account_address"]
            ]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assumed_body_1 = {
            "token": {
                "token_address": token_address_1,
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },

            "balance": 1000000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }
        assumed_body_2 = {
            "token": {
                "token_address": token_address_2,
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "balance": 1000000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }
        count = 0
        for token in resp.json["data"]:
            if token["token"]["token_address"] == token_address_1:
                count += 1
                assert token == assumed_body_1
            if token["token"]["token_address"] == token_address_2:
                count += 1
                assert token == assumed_body_2
        assert count == 2

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # Invalid Parameter Error
    # No request-body
    def test_error_1(self, client):
        config.SHARE_TOKEN_ENABLED = True

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": "required field"
            }
        }

    # Error_2
    # Invalid Parameter Error
    # No headers
    def test_error_2(self, client):
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}

        config.SHARE_TOKEN_ENABLED = True

        headers = {}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # Error_3_1
    # Invalid Parameter Error
    # account_address: invalid address
    def test_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # short address
        request_params = {"account_address_list": [account_address]}

        config.SHARE_TOKEN_ENABLED = True

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid account address"
        }

    # Error_3_2
    # Invalid Parameter Error
    # account_address: invalid type
    def test_error_3_2(self, client):
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        config.SHARE_TOKEN_ENABLED = True

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl,
            headers=headers,
            body=request_body
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": {
                    "0": "must be of string type"
                }
            }
        }

    # Error_4
    # Not Supported Error
    # Token is not listed
    def test_error_4(self, client):
        config.SHARE_TOKEN_ENABLED = False
        resp = client.simulate_post(self.apiurl)
        # Assertion
        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/Position/Share"
        }
