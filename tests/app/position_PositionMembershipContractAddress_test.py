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
from eth_typing import ChecksumAddress
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
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


class TestPositionMembershipContractAddress:
    # Test API
    apiurl = "/Position/{account_address}/Membership/{contract_address}"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account: ChecksumAddress, exchange_contract, token_list_contract):
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
        token = membership_issue(TestPositionMembershipContractAddress.issuer, args)
        membership_register_list(TestPositionMembershipContractAddress.issuer, token, token_list_contract)
        membership_transfer_to_exchange(
            TestPositionMembershipContractAddress.issuer,
            {"address": account},
            token,
            1000000
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(account: ChecksumAddress, exchange_contract, token_list_contract, commitment):
        # Issue token
        token = TestPositionMembershipContractAddress.create_balance_data(
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
            createOrder(token['address'], commitment, 10000, False, agent). \
            transact({'from': account, 'gas': 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)

        return token

    # Prepare non balance data
    # balance = 0
    @staticmethod
    def create_non_balance_data(account, to_account, exchange_contract, token_list_contract):
        # Issue token
        token = TestPositionMembershipContractAddress.create_balance_data(
            account, exchange_contract, token_list_contract)

        # Transfer all amount
        membership_transfer_to_exchange(
            account,
            {"address": to_account},
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
    # balance: 1000000
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
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
            resp = client.get(
                self.apiurl.format(account_address=self.account_1,
                                   contract_address=token_2["address"]),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_2["address"],
                'token_template': 'IbetMembership',
                'owner_address': self.issuer,
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''}, {'id': 2, 'url': ''}, {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': config.ZERO_ADDRESS,
            },
            "balance": 1000000,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }

    # <Normal_2>
    # balance: 999900, exchange_balance: 100
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
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
            resp = client.get(
                self.apiurl.format(account_address=self.account_1,
                                   contract_address=token_3["address"]),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_3["address"],
                'token_template': 'IbetMembership',
                'owner_address': self.issuer,
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''}, {'id': 2, 'url': ''}, {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_contract["address"],
            },
            "balance": 999900,
            "exchange_balance": 0,
            "exchange_commitment": 100,
        }

    # <Normal_3>
    # balance: 0, exchange_balance: 1000000
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
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
            resp = client.get(
                self.apiurl.format(account_address=self.account_1,
                                   contract_address=token_4["address"]),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_4["address"],
                'token_template': 'IbetMembership',
                'owner_address': self.issuer,
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''}, {'id': 2, 'url': ''}, {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_contract["address"],
            },
            "balance": 0,
            "exchange_balance": 0,
            "exchange_commitment": 1000000,
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client: TestClient, session: Session):

        account_address = self.account_1
        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        with mock.patch("app.config.MEMBERSHIP_TOKEN_ENABLED", False):
            resp = client.get(
                self.apiurl.format(account_address=account_address, contract_address=contract_address)
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": f"method: GET, url: /Position/{account_address}/Membership/{contract_address}"
        }

    # <Error_2>
    # ParameterError: invalid account_address
    def test_error_2(self, client: TestClient, session: Session):

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address="invalid", contract_address=contract_address),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid account_address"
        }

    # <Error_3>
    # ParameterError: invalid contract_address
    def test_error_3(self, client: TestClient, session: Session):

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=self.account_1, contract_address="invalid"),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid contract_address"
        }

    # <Error_4>
    # DataNotExistsError: not listing
    def test_error_4(self, client: TestClient, session: Session):

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=self.account_1, contract_address=contract_address),
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}"
        }

    # <Error_5>
    # DataNotExistsError: not position
    def test_error_5(self, client: TestClient, session: Session, shared_contract):
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, {"address": config.ZERO_ADDRESS}, token_list_contract)
        self.list_token(token_non["address"], session)  # not target

        contract_address = token_non["address"]

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1,
                                   contract_address=contract_address),
            )

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}"
        }
