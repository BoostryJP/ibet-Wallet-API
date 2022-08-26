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
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest import mock

from app import config
from app.model.db import Listing
from tests.account_config import eth_account
from tests.utils import (
    PersonalInfoUtils,
    IbetShareUtils
)


class TestPositionShareContractAddress:
    # Test API
    apiurl = "/Position/{account_address}/Share/{contract_address}"

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
        issuer_address = TestPositionShareContractAddress.issuer["account_address"]

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
        issuer_address = TestPositionShareContractAddress.issuer["account_address"]

        # Issue token
        token = TestPositionShareContractAddress.create_balance_data(
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
    def create_commitment_data(account,
                               exchange_contract,
                               personal_info_contract,
                               token_list_contract,
                               commitment):
        # Issue token
        token = TestPositionShareContractAddress.create_balance_data(
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
    def create_non_balance_data(account,
                                to_account,
                                exchange_contract,
                                personal_info_contract,
                                token_list_contract):
        issuer_address = TestPositionShareContractAddress.issuer["account_address"]

        # Issue token
        token = TestPositionShareContractAddress.create_balance_data(
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
    # balance: 1000000
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
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
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_2.address
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_2.address,
                'token_template': 'IbetShare',
                'owner_address': self.issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'principal_value': 1000,
                'dividend_information': {
                    'dividends': 1.01,
                    'dividend_record_date': '20200401',
                    'dividend_payment_date': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'is_offering': False,
                'status': True,
                'transfer_approval_required': False,
                'is_canceled': False,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': config.ZERO_ADDRESS,
                'personal_info_address': personal_info_contract["address"],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000},
            "balance": 1000000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }

    # <Normal_2>
    # balance: 999900, pending_transfer: 100
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
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
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_3.address
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_3.address,
                'token_template': 'IbetShare',
                'owner_address': self.issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'principal_value': 1000,
                'dividend_information': {
                    'dividends': 1.01,
                    'dividend_record_date': '20200401',
                    'dividend_payment_date': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'is_offering': False,
                'status': True,
                'transfer_approval_required': True,
                'is_canceled': False,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': config.ZERO_ADDRESS,
                'personal_info_address': personal_info_contract["address"],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000},
            "balance": 999900,
            "pending_transfer": 100,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }

    # <Normal_3>
    # balance: 0, pending_transfer: 1000000
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
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
            token_list_contract, 100
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
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_4.address
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_4.address,
                'token_template': 'IbetShare',
                'owner_address': self.issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'principal_value': 1000,
                'dividend_information': {
                    'dividends': 1.01,
                    'dividend_record_date': '20200401',
                    'dividend_payment_date': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'is_offering': False,
                'status': True,
                'transfer_approval_required': True,
                'is_canceled': False,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': config.ZERO_ADDRESS,
                'personal_info_address': personal_info_contract["address"],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000},
            "balance": 0,
            "pending_transfer": 1000000,
            "exchange_balance": 0,
            "exchange_commitment": 0,
        }

    # <Normal_4>
    # balance: 999900, exchange_balance: 100
    def test_normal_4(self, client: TestClient, session: Session, shared_contract):
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
            token_list_contract, 100
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
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_5.address
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_5.address,
                'token_template': 'IbetShare',
                'owner_address': self.issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'principal_value': 1000,
                'dividend_information': {
                    'dividends': 1.01,
                    'dividend_record_date': '20200401',
                    'dividend_payment_date': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'is_offering': False,
                'status': True,
                'transfer_approval_required': False,
                'is_canceled': False,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_contract["address"],
                'personal_info_address': personal_info_contract["address"],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000},
            "balance": 999900,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 100,
        }

    # <Normal_5>
    # balance: 0, exchange_balance: 1000000
    def test_normal_5(self, client: TestClient, session: Session, shared_contract):
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
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_6.address
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                'token_address': token_6.address,
                'token_template': 'IbetShare',
                'owner_address': self.issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 1000,
                'principal_value': 1000,
                'dividend_information': {
                    'dividends': 1.01,
                    'dividend_record_date': '20200401',
                    'dividend_payment_date': '20200502'
                },
                'cancellation_date': '20200603',
                'memo': 'メモ',
                'transferable': True,
                'is_offering': False,
                'status': True,
                'transfer_approval_required': False,
                'is_canceled': False,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'tradable_exchange': exchange_contract["address"],
                'personal_info_address': personal_info_contract["address"],
                'max_holding_quantity': 1,
                'max_sell_amount': 1000},
            "balance": 0,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 1000000,
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client: TestClient, session: Session):

        account_address = self.account_1["account_address"]
        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        with mock.patch("app.config.SHARE_TOKEN_ENABLED", False):
            resp = client.get(
                self.apiurl.format(account_address=account_address, contract_address=contract_address)
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": f"method: GET, url: /Position/{account_address}/Share/{contract_address}"
        }

    # <Error_2>
    # ParameterError: invalid account_address
    def test_error_2(self, client: TestClient, session: Session):

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        resp = client.get(
            self.apiurl.format(
                account_address="invalid",
                contract_address=contract_address
            ),
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
            self.apiurl.format(
                account_address=self.account_1["account_address"],
                contract_address="invalid"
            ),
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
            self.apiurl.format(
                account_address=self.account_1["account_address"],
                contract_address=contract_address
            ),
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
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1, self.account_2, self.zero_address, personal_info_contract,
            token_list_contract)
        self.list_token(token_non.address, session)  # not target

        contract_address = token_non.address

        with mock.patch("app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=contract_address
                ),
            )

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}"
        }
