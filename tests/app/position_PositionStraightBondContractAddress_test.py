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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import IDXBondToken, IDXLockedPosition, IDXPosition, Listing
from tests.account_config import eth_account
from tests.contract_modules import (
    bond_lock,
    bond_transfer_to_exchange,
    issue_bond_token,
    register_bond_list,
    transfer_bond_token,
)
from tests.utils import PersonalInfoUtils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionStraightBondContractAddress:
    # Test API
    apiurl = "/Position/{account_address}/StraightBond/{contract_address}"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(
        account, exchange_contract, personal_info_contract, token_list_contract
    ):
        issuer_address = TestPositionStraightBondContractAddress.issuer[
            "account_address"
        ]

        # Issue token
        args = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract["address"],
            "faceValue": 10000,
            "interestRate": 602,
            "interestPaymentDate1": "0101",
            "interestPaymentDate2": "0201",
            "interestPaymentDate3": "0301",
            "interestPaymentDate4": "0401",
            "interestPaymentDate5": "0501",
            "interestPaymentDate6": "0601",
            "interestPaymentDate7": "0701",
            "interestPaymentDate8": "0801",
            "interestPaymentDate9": "0901",
            "interestPaymentDate10": "1001",
            "interestPaymentDate11": "1101",
            "interestPaymentDate12": "1201",
            "redemptionDate": "20191231",
            "redemptionValue": 10000,
            "returnDate": "20191231",
            "returnAmount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "memo": "メモ",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "personalInfoAddress": personal_info_contract["address"],
            "transferable": True,
            "isRedeemed": False,
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
        }
        token = issue_bond_token(TestPositionStraightBondContractAddress.issuer, args)
        register_bond_list(
            TestPositionStraightBondContractAddress.issuer, token, token_list_contract
        )
        PersonalInfoUtils.register(
            tx_from=account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address,
        )
        bond_transfer_to_exchange(
            TestPositionStraightBondContractAddress.issuer,
            {"address": account["account_address"]},
            token,
            1000000,
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(
        account,
        exchange_contract,
        personal_info_contract,
        token_list_contract,
        commitment,
    ):
        # Issue token
        token = TestPositionStraightBondContractAddress.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract
        )

        # Sell order
        agent = eth_account["agent"]
        bond_transfer_to_exchange(account, exchange_contract, token, commitment)
        ExchangeContract = Contract.get_contract(
            "IbetExchange", exchange_contract["address"]
        )
        tx_hash = ExchangeContract.functions.createOrder(
            token["address"], commitment, 10000, False, agent["account_address"]
        ).transact({"from": account["account_address"], "gas": 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)

        return token

    # Prepare non balance data
    # balance = 0
    @staticmethod
    def create_non_balance_data(
        account,
        to_account,
        exchange_contract,
        personal_info_contract,
        token_list_contract,
    ):
        issuer_address = TestPositionStraightBondContractAddress.issuer[
            "account_address"
        ]

        # Issue token
        token = TestPositionStraightBondContractAddress.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract
        )

        # Transfer all amount
        PersonalInfoUtils.register(
            tx_from=to_account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address,
        )
        bond_transfer_to_exchange(
            account, {"address": to_account["account_address"]}, token, 1000000
        )

        return token

    @staticmethod
    def create_idx_position(
        session: Session,
        token_address: str,
        account_address: str,
        balance: int | None = None,
        pending_transfer: int | None = None,
        exchange_balance: int | None = None,
        exchange_commitment: int | None = None,
    ):
        if (
            not balance
            and not exchange_balance
            and not exchange_commitment
            and not pending_transfer
        ):
            return
        idx_position = IDXPosition()
        idx_position.token_address = token_address
        idx_position.account_address = account_address
        if balance:
            idx_position.balance = balance
        if pending_transfer:
            idx_position.pending_transfer = pending_transfer
        if exchange_balance:
            idx_position.exchange_balance = exchange_balance
        if exchange_commitment:
            idx_position.exchange_commitment = exchange_commitment
        session.merge(idx_position)
        session.commit()
        pass

    @staticmethod
    def create_idx_token(
        session: Session,
        token_address: str,
        personal_info_address: str,
        exchange_address: str | None,
    ):
        # Issue token
        idx_token = IDXBondToken()
        idx_token.token_address = token_address
        idx_token.owner_address = TestPositionStraightBondContractAddress.issuer[
            "account_address"
        ]
        idx_token.company_name = ""
        idx_token.rsa_publickey = ""
        idx_token.name = "テスト債券"
        idx_token.symbol = "BOND"
        idx_token.token_template = "IbetStraightBond"
        idx_token.total_supply = 1000000
        idx_token.face_value = 10000
        idx_token.interest_rate = 0.0602
        idx_token.interest_payment_date = [
            "0101",
            "0201",
            "0301",
            "0401",
            "0501",
            "0601",
            "0701",
            "0801",
            "0901",
            "1001",
            "1101",
            "1201",
        ]
        idx_token.redemption_date = "20191231"
        idx_token.redemption_value = 10000
        idx_token.return_date = "20191231"
        idx_token.return_amount = "商品券をプレゼント"
        idx_token.purpose = "新商品の開発資金として利用。"
        idx_token.max_holding_quantity = 1
        idx_token.max_sell_amount = 1000
        idx_token.contact_information = "問い合わせ先"
        idx_token.privacy_policy = "プライバシーポリシー"
        idx_token.is_redeemed = False
        idx_token.transferable = True
        idx_token.is_offering = False
        idx_token.tradable_exchange = exchange_address
        idx_token.status = True
        idx_token.memo = "メモ"
        idx_token.personal_info_address = personal_info_address
        idx_token.transfer_approval_required = False
        idx_token.face_value_currency = ""
        idx_token.interest_payment_currency = ""
        idx_token.redemption_value_currency = ""
        idx_token.base_fx_rate = 0.0

        session.add(idx_token)
        session.commit()

    @staticmethod
    def create_idx_locked_position(
        session: Session,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
    ):
        # Issue token
        idx_locked = IDXLockedPosition()
        idx_locked.token_address = token_address
        idx_locked.lock_address = lock_address
        idx_locked.account_address = account_address
        idx_locked.value = value
        session.add(idx_locked)
        session.commit()

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
        config.BOND_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

        session.commit()

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_2["address"],
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_2["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": config.ZERO_ADDRESS,
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            },
            "balance": 1000000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "locked": None,
        }

    # <Normal_2>
    # balance: 999900, exchange_balance: 100
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

        session.commit()

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_3["address"],
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_3["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": exchange_contract["address"],
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            },
            "balance": 999900,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 100,
            "locked": None,
        }

    # <Normal_3>
    # balance: 0, exchange_balance: 1000000
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

        session.commit()

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_4["address"],
                ),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_4["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": exchange_contract["address"],
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "JPY",
                "interest_payment_currency": "JPY",
                "redemption_value_currency": "JPY",
                "base_fx_rate": 0.0,
            },
            "balance": 0,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 1000000,
            "locked": None,
        }

    # <Normal_4>
    # balance: 1000000
    # Indexed: <Normal_1>
    def test_normal_4(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1["address"], session)  # not target
        self.create_idx_token(
            session,
            token_1["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_2 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_2["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2["address"], session)  # not target
        self.create_idx_token(
            session,
            token_2["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_3 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_3["address"],
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3["address"], session)  # not target
        self.create_idx_token(
            session,
            token_3["address"],
            personal_info_contract["address"],
            exchange_contract["address"],
        )

        token_4 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_4["address"],
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4["address"], session)
        self.create_idx_token(
            session,
            token_4["address"],
            personal_info_contract["address"],
            exchange_contract["address"],
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_2["address"],
                ),
                params={"enable_index": True},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_2["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": config.ZERO_ADDRESS,
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "",
                "interest_payment_currency": "",
                "redemption_value_currency": "",
                "base_fx_rate": 0.0,
            },
            "balance": 1000000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "locked": 0,
        }

    # <Normal_5>
    # balance: 999900, exchange_balance: 100
    # Indexed: <Normal_2>
    def test_normal_5(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1["address"], session)  # not target
        self.create_idx_token(
            session,
            token_1["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_2 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_2["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2["address"], session)  # not target
        self.create_idx_token(
            session,
            token_2["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_3 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_3["address"],
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3["address"], session)  # not target
        self.create_idx_token(
            session,
            token_3["address"],
            personal_info_contract["address"],
            exchange_contract["address"],
        )

        token_4 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_4["address"],
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4["address"], session)
        self.create_idx_token(
            session,
            token_4["address"],
            personal_info_contract["address"],
            exchange_contract["address"],
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_3["address"],
                ),
                params={"enable_index": True},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_3["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": exchange_contract["address"],
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "",
                "interest_payment_currency": "",
                "redemption_value_currency": "",
                "base_fx_rate": 0.0,
            },
            "balance": 999900,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 100,
            "locked": 0,
        }

    # <Normal_6>
    # balance: 0, exchange_balance: 1000000
    # Indexed: <Normal_3>
    def test_normal_6(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetStraightBondExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1["address"], session)  # not target
        self.create_idx_token(
            session,
            token_1["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_2 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_2["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2["address"], session)  # not target
        self.create_idx_token(
            session,
            token_2["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_3 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_3["address"],
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3["address"], session)  # not target
        self.create_idx_token(
            session,
            token_3["address"],
            personal_info_contract["address"],
            exchange_contract["address"],
        )

        token_4 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_4["address"],
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4["address"], session)
        self.create_idx_token(
            session,
            token_4["address"],
            personal_info_contract["address"],
            exchange_contract["address"],
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(
            session,
            token_non["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_4["address"],
                ),
                params={"enable_index": True},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_4["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": exchange_contract["address"],
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "",
                "interest_payment_currency": "",
                "redemption_value_currency": "",
                "base_fx_rate": 0.0,
            },
            "balance": 0,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 1000000,
            "locked": 0,
        }

    # <Normal_7>
    # locked amount
    def test_normal_7(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_1 = self.create_balance_data(
            self.account_1,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )

        bond_lock(
            invoker=self.account_1,
            token=token_1,
            lock_address=self.account_2["account_address"],
            amount=1000,
        )
        bond_lock(
            invoker=self.account_1,
            token=token_1,
            lock_address=self.issuer["account_address"],
            amount=2000,
        )
        transfer_bond_token(
            invoker=self.account_1, to=self.account_2, token=token_1, amount=5000
        )
        bond_lock(
            invoker=self.account_2,
            token=token_1,
            lock_address=self.issuer["account_address"],
            amount=5000,
        )

        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000 - 3000,
        )
        self.create_idx_locked_position(
            session,
            token_1["address"],
            self.account_2["account_address"],
            self.account_1["account_address"],
            1000,
        )
        self.create_idx_locked_position(
            session,
            token_1["address"],
            self.issuer["account_address"],
            self.account_1["account_address"],
            2000,
        )
        self.create_idx_locked_position(
            session,
            token_1["address"],
            self.issuer["account_address"],
            self.account_2["account_address"],
            5000,
        )
        self.list_token(token_1["address"], session)
        self.create_idx_token(
            session,
            token_1["address"],
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=token_1["address"],
                ),
                params={"enable_index": True},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "token": {
                "token_address": token_1["address"],
                "token_template": "IbetStraightBond",
                "owner_address": self.issuer["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "max_holding_quantity": 1,
                "max_sell_amount": 1000,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "is_redeemed": False,
                "transferable": True,
                "is_offering": False,
                "tradable_exchange": config.ZERO_ADDRESS,
                "status": True,
                "memo": "メモ",
                "personal_info_address": personal_info_contract["address"],
                "transfer_approval_required": False,
                "face_value_currency": "",
                "interest_payment_currency": "",
                "redemption_value_currency": "",
                "base_fx_rate": 0.0,
            },
            "balance": 997000,
            "pending_transfer": 0,
            "exchange_balance": 0,
            "exchange_commitment": 0,
            "locked": 3000,
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client: TestClient, session: Session):
        account_address = self.account_1["account_address"]
        config.BOND_TOKEN_ENABLED = False

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        with mock.patch("app.config.BOND_TOKEN_ENABLED", False):
            resp = client.get(
                self.apiurl.format(
                    account_address=account_address, contract_address=contract_address
                )
            )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": f"method: GET, url: /Position/{account_address}/StraightBond/{contract_address}",
        }

    # <Error_2>
    # ParameterError: invalid account_address
    def test_error_2(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        resp = client.get(
            self.apiurl.format(
                account_address="invalid", contract_address=contract_address
            ),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "account_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "invalid",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_3>
    # ParameterError: invalid contract_address
    def test_error_3(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl.format(
                account_address=self.account_1["account_address"],
                contract_address="invalid",
            ),
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "token_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "invalid",
                    "ctx": {"error": {}},
                }
            ],
        }

    # <Error_4_1>
    # DataNotExistsError: not listing
    def test_error_4_1(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        resp = client.get(
            self.apiurl.format(
                account_address=self.account_1["account_address"],
                contract_address=contract_address,
            ),
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}",
        }

    # <Error_4_2>
    # DataNotExistsError: not listing
    # enable_index: True
    def test_error_4_2(self, client: TestClient, session: Session):
        config.BOND_TOKEN_ENABLED = True

        contract_address = "0x1234567890abCdFe1234567890ABCdFE12345678"

        # Request target API
        resp = client.get(
            self.apiurl.format(
                account_address=self.account_1["account_address"],
                contract_address=contract_address,
            ),
            params={"enable_index": True},
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}",
        }

    # <Error_5_1>
    # DataNotExistsError: not position
    def test_error_5_1(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

        contract_address = token_non["address"]

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=contract_address,
                ),
            )

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}",
        }

    # <Error_5_2>
    # DataNotExistsError: not position
    # enable_index: True
    def test_error_5_2(self, client: TestClient, session: Session, shared_contract):
        config.BOND_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

        contract_address = token_non["address"]

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(
                    account_address=self.account_1["account_address"],
                    contract_address=contract_address,
                ),
                params={"enable_index": True},
            )

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"contract_address: {contract_address}",
        }
