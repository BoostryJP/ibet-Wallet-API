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

from app import config
from app.model.db import (
    IDXLockedPosition,
    IDXPosition,
    IDXShareToken,
    IDXTokenListRegister,
    Listing,
)
from tests.account_config import eth_account
from tests.contract_modules import share_lock, transfer_share_token
from tests.utils import IbetShareUtils, PersonalInfoUtils


class TestPositionShare:
    # Test API
    apiurl = "/Position/{account_address}/Share"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]
    zero_address = {"address": config.ZERO_ADDRESS}

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(
        account, exchange_contract, personal_info_contract, token_list_contract
    ):
        issuer_address = TestPositionShare.issuer["account_address"]

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
            "transferable": True,
        }
        token = IbetShareUtils.issue(tx_from=issuer_address, args=args)
        IbetShareUtils.register_token_list(
            tx_from=issuer_address,
            token_address=token.address,
            token_list_contract_address=token_list_contract["address"],
        )
        PersonalInfoUtils.register(
            tx_from=account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address,
        )
        IbetShareUtils.transfer_to_exchange(
            tx_from=issuer_address,
            exchange_address=account["account_address"],
            token_address=token.address,
            amount=1000000,
        )

        return token

    # Prepare pending_transfer data
    # balance = 1000000, pending_transfer = [args pending_transfer]
    @staticmethod
    def create_pending_transfer_data(
        account,
        to_account,
        exchange_contract,
        personal_info_contract,
        token_list_contract,
        pending_transfer,
    ):
        issuer_address = TestPositionShare.issuer["account_address"]

        # Issue token
        token = TestPositionShare.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract
        )

        # Apply for transfer
        IbetShareUtils.set_transfer_approval_required(
            tx_from=issuer_address, token_address=token.address, required=True
        )
        PersonalInfoUtils.register(
            tx_from=to_account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address,
        )
        IbetShareUtils.apply_for_transfer(
            tx_from=account["account_address"],
            token_address=token.address,
            to=to_account["account_address"],
            value=pending_transfer,
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
        token = TestPositionShare.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract
        )

        # Sell order
        IbetShareUtils.sell(
            tx_from=account["account_address"],
            exchange_address=exchange_contract["address"],
            token_address=token.address,
            amount=commitment,
            price=1000,
        )

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
        issuer_address = TestPositionShare.issuer["account_address"]

        # Issue token
        token = TestPositionShare.create_balance_data(
            account, exchange_contract, personal_info_contract, token_list_contract
        )

        # Transfer all amount
        PersonalInfoUtils.register(
            tx_from=to_account["account_address"],
            personal_info_address=personal_info_contract["address"],
            link_address=issuer_address,
        )
        IbetShareUtils.transfer_to_exchange(
            tx_from=account["account_address"],
            exchange_address=to_account["account_address"],
            token_address=token.address,
            amount=1000000,
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
        idx_token = IDXShareToken()
        idx_token.token_address = token_address
        idx_token.owner_address = TestPositionShare.issuer["account_address"]
        idx_token.company_name = ""
        idx_token.rsa_publickey = ""
        idx_token.name = "テスト株式"
        idx_token.symbol = "SHARE"
        idx_token.token_template = "IbetShare"
        idx_token.total_supply = 1000000
        idx_token.issue_price = 1000
        idx_token.principal_value = 1000
        idx_token.dividend_information = {
            "dividends": 0.0000000000101,
            "dividend_record_date": "20200401",
            "dividend_payment_date": "20200502",
        }
        idx_token.cancellation_date = "20200603"
        idx_token.memo = "メモ"
        idx_token.transferable = True
        idx_token.is_offering = False
        idx_token.status = True
        idx_token.transfer_approval_required = False
        idx_token.is_canceled = False
        idx_token.contact_information = "問い合わせ先"
        idx_token.privacy_policy = "プライバシーポリシー"
        idx_token.tradable_exchange = exchange_address
        idx_token.personal_info_address = personal_info_address
        idx_token.require_personal_info_registered = True
        idx_token.max_holding_quantity = 1
        idx_token.max_sell_amount = 1000
        session.add(idx_token)
        idx_token_list_item = IDXTokenListRegister()
        idx_token_list_item.token_address = token_address
        idx_token_list_item.token_template = "IbetShare"
        idx_token_list_item.owner_address = TestPositionShare.issuer["account_address"]
        session.add(idx_token_list_item)
        session.commit()

    @staticmethod
    def create_idx_locked_position(
        session: Session,
        token_address: str,
        lock_address: str,
        account_address: str,
        value: int,
    ):
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
    # List all positions
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_1.address, session)

        token_2 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_2.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_3 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_3.address, session)

        token_4 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_4.address, session)

        token_5 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_5.address, session)

        token_6 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_6.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        session.commit()

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
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
                    "locked": None,
                },
                {
                    "token_address": token_2.address,
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": None,
                },
                {
                    "token_address": token_3.address,
                    "balance": 999900,
                    "pending_transfer": 100,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": None,
                },
                {
                    "token_address": token_4.address,
                    "balance": 0,
                    "pending_transfer": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": None,
                },
                {
                    "token_address": token_5.address,
                    "balance": 999900,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "locked": None,
                },
                {
                    "token_address": token_6.address,
                    "balance": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "locked": None,
                },
            ],
        }

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_1.address, session)

        token_2 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_2.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_3 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_3.address, session)

        token_4 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_4.address, session)

        token_5 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.list_token(token_5.address, session)

        token_6 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.list_token(token_6.address, session)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_non.address, session)  # not target

        session.commit()

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={
                    "include_token_details": "false",
                    "offset": 1,
                    "limit": 2,
                },
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["data"] == {
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
                    "locked": None,
                },
                {
                    "token_address": token_3.address,
                    "balance": 999900,
                    "pending_transfer": 100,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": None,
                },
            ],
        }

    # <Normal_3>
    # token details
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.list_token(token_1.address, session)

        session.commit()

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={
                    "include_token_details": "true",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "positions": [
                {
                    "token": {
                        "token_address": token_1.address,
                        "token_template": "IbetShare",
                        "owner_address": self.issuer["account_address"],
                        "company_name": "",
                        "rsa_publickey": "",
                        "name": "テスト株式",
                        "symbol": "SHARE",
                        "total_supply": 1000000,
                        "issue_price": 1000,
                        "principal_value": 1000,
                        "dividend_information": {
                            "dividends": 0.0000000000101,
                            "dividend_record_date": "20200401",
                            "dividend_payment_date": "20200502",
                        },
                        "cancellation_date": "20200603",
                        "memo": "メモ",
                        "transferable": True,
                        "is_offering": False,
                        "status": True,
                        "transfer_approval_required": False,
                        "is_canceled": False,
                        "contact_information": "問い合わせ先",
                        "privacy_policy": "プライバシーポリシー",
                        "tradable_exchange": config.ZERO_ADDRESS,
                        "personal_info_address": personal_info_contract["address"],
                        "require_personal_info_registered": True,
                        "max_holding_quantity": 1,
                        "max_sell_amount": 1000,
                    },
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": None,
                },
            ],
        }

    # <Normal_4>
    # List all positions
    # Indexed: <Normal_1>
    def test_normal_4(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session, token_1.address, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_1.address, session)  # not target
        self.create_idx_token(
            session,
            token_1.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_2 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session, token_2.address, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_2.address, session)  # not target
        self.create_idx_token(
            session,
            token_2.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_3 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_3.address,
            self.account_1["account_address"],
            balance=999900,
            pending_transfer=100,
        )
        self.list_token(token_3.address, session)  # not target
        self.create_idx_token(
            session,
            token_3.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_4 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_4.address,
            self.account_1["account_address"],
            pending_transfer=1000000,
        )
        self.list_token(token_4.address, session)
        self.create_idx_token(
            session,
            token_4.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_5 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_5.address,
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_5.address, session)
        self.create_idx_token(
            session,
            token_5.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_6 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_6.address,
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_6.address, session)
        self.create_idx_token(
            session,
            token_6.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={"enable_index": "true"},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
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
                    "locked": 0,
                },
                {
                    "token_address": token_2.address,
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
                {
                    "token_address": token_3.address,
                    "balance": 999900,
                    "pending_transfer": 100,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
                {
                    "token_address": token_4.address,
                    "balance": 0,
                    "pending_transfer": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
                {
                    "token_address": token_5.address,
                    "balance": 999900,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "locked": 0,
                },
                {
                    "token_address": token_6.address,
                    "balance": 0,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "locked": 0,
                },
            ],
        }

    # <Normal_5>
    # Pagination
    # Indexed: <Normal_2>
    def test_normal_5(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetShareExchange"]
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session, token_1.address, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_1.address, session)  # not target
        self.create_idx_token(
            session,
            token_1.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_2 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session, token_2.address, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_2.address, session)  # not target
        self.create_idx_token(
            session,
            token_2.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_3 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_3.address,
            self.account_1["account_address"],
            balance=999900,
            pending_transfer=100,
        )
        self.list_token(token_3.address, session)  # not target
        self.create_idx_token(
            session,
            token_3.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_4 = self.create_pending_transfer_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_4.address,
            self.account_1["account_address"],
            pending_transfer=1000000,
        )
        self.list_token(token_4.address, session)
        self.create_idx_token(
            session,
            token_4.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_5 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            100,
        )
        self.create_idx_position(
            session,
            token_5.address,
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_5.address, session)
        self.create_idx_token(
            session,
            token_5.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_6 = self.create_commitment_data(
            self.account_1,
            exchange_contract,
            personal_info_contract,
            token_list_contract,
            1000000,
        )
        self.create_idx_position(
            session,
            token_6.address,
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_6.address, session)
        self.create_idx_token(
            session,
            token_6.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non.address,
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non.address, session)  # not target
        self.create_idx_token(
            session,
            token_non.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={
                    "include_token_details": "false",
                    "enable_index": "true",
                    "offset": 1,
                    "limit": 2,
                },
            )

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["data"] == {
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
                    "locked": 0,
                },
                {
                    "token_address": token_3.address,
                    "balance": 999900,
                    "pending_transfer": 100,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
            ],
        }

    # <Normal_6>
    # token details
    # Indexed: <Normal_3>
    def test_normal_6(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )
        self.create_idx_position(
            session, token_1.address, self.account_1["account_address"], balance=1000000
        )
        self.list_token(token_1.address, session)
        self.create_idx_token(
            session,
            token_1.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={"include_token_details": "true", "enable_index": "true"},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "positions": [
                {
                    "token": {
                        "token_address": token_1.address,
                        "token_template": "IbetShare",
                        "owner_address": self.issuer["account_address"],
                        "company_name": "",
                        "rsa_publickey": "",
                        "name": "テスト株式",
                        "symbol": "SHARE",
                        "total_supply": 1000000,
                        "issue_price": 1000,
                        "principal_value": 1000,
                        "dividend_information": {
                            "dividends": 0.0000000000101,
                            "dividend_record_date": "20200401",
                            "dividend_payment_date": "20200502",
                        },
                        "cancellation_date": "20200603",
                        "memo": "メモ",
                        "transferable": True,
                        "is_offering": False,
                        "status": True,
                        "transfer_approval_required": False,
                        "is_canceled": False,
                        "contact_information": "問い合わせ先",
                        "privacy_policy": "プライバシーポリシー",
                        "tradable_exchange": config.ZERO_ADDRESS,
                        "personal_info_address": personal_info_contract["address"],
                        "require_personal_info_registered": True,
                        "max_holding_quantity": 1,
                        "max_sell_amount": 1000,
                    },
                    "balance": 1000000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 0,
                },
            ],
        }

    # <Normal_7>
    # locked amount
    def test_normal_7(self, client: TestClient, session: Session, shared_contract):
        config.SHARE_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]

        # Prepare data
        token_1 = self.create_balance_data(
            self.account_1,
            self.zero_address,
            personal_info_contract,
            token_list_contract,
        )

        share_lock(
            invoker=self.account_1,
            token={"address": token_1.address},
            lock_address=self.account_2["account_address"],
            amount=1000,
        )
        share_lock(
            invoker=self.account_1,
            token={"address": token_1.address},
            lock_address=self.issuer["account_address"],
            amount=2000,
        )
        transfer_share_token(
            invoker=self.account_1,
            to=self.account_2,
            token={"address": token_1.address},
            amount=5000,
        )
        share_lock(
            invoker=self.account_2,
            token={"address": token_1.address},
            lock_address=self.issuer["account_address"],
            amount=5000,
        )

        self.create_idx_position(
            session,
            token_1.address,
            self.account_1["account_address"],
            balance=1000000 - 3000,
        )
        self.create_idx_locked_position(
            session,
            token_1.address,
            self.account_2["account_address"],
            self.account_1["account_address"],
            1000,
        )
        self.create_idx_locked_position(
            session,
            token_1.address,
            self.issuer["account_address"],
            self.account_1["account_address"],
            2000,
        )
        self.create_idx_locked_position(
            session,
            token_1.address,
            self.issuer["account_address"],
            self.account_2["account_address"],
            5000,
        )
        self.list_token(token_1.address, session)
        self.create_idx_token(
            session,
            token_1.address,
            personal_info_contract["address"],
            config.ZERO_ADDRESS,
        )

        with mock.patch(
            "app.config.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]
        ):
            # Request target API
            resp = client.get(
                self.apiurl.format(account_address=self.account_1["account_address"]),
                params={"enable_index": "true"},
            )

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "result_set": {
                "count": 1,
                "offset": None,
                "limit": None,
                "total": 1,
            },
            "positions": [
                {
                    "token_address": token_1.address,
                    "balance": 997000,
                    "pending_transfer": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "locked": 3000,
                },
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client: TestClient, session: Session):
        config.SHARE_TOKEN_ENABLED = False

        account_address = self.account_1["account_address"]

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=account_address),
        )

        # Assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": f"method: GET, url: /Position/{account_address}/Share",
        }

    # <Error_2>
    # ParameterError: invalid account_address
    def test_error_2(self, client: TestClient, session: Session):
        config.SHARE_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address="invalid"),
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
    # ParameterError: offset/limit(minus value)
    def test_error_3(self, client: TestClient, session: Session):
        config.SHARE_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=self.account_1["account_address"]),
            params={
                "offset": -1,
                "limit": -1,
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "offset"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
                {
                    "ctx": {"ge": 0},
                    "input": "-1",
                    "loc": ["query", "limit"],
                    "msg": "Input should be greater than or equal to 0",
                    "type": "greater_than_equal",
                },
            ],
            "message": "Invalid Parameter",
        }

    # <Error_4>
    # ParameterError: offset/limit(not int), include_token_details(not bool)
    def test_error_4(self, client: TestClient, session: Session):
        config.SHARE_TOKEN_ENABLED = True

        # Request target API
        resp = client.get(
            self.apiurl.format(account_address=self.account_1["account_address"]),
            params={
                "include_token_details": "test",
                "offset": "test",
                "limit": "test",
            },
        )

        # Assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "test",
                    "loc": ["query", "offset"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "limit"],
                    "msg": "Input should be a valid integer, unable to parse "
                    "string as an integer",
                    "type": "int_parsing",
                },
                {
                    "input": "test",
                    "loc": ["query", "include_token_details"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "type": "bool_parsing",
                },
            ],
            "message": "Invalid Parameter",
        }
