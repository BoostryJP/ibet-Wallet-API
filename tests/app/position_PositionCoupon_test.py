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
from app.model.db import (
    IDXConsumeCoupon,
    IDXCouponToken,
    IDXPosition,
    IDXTokenListItem,
    IDXTransfer,
    IDXTransferSourceEventType,
    Listing,
)
from tests.account_config import eth_account
from tests.contract_modules import (
    consume_coupon_token,
    coupon_register_list,
    issue_coupon_token,
    transfer_coupon_token,
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestPositionCoupon:
    # Test API
    apiurl = "/Position/{account_address}/Coupon"

    issuer = eth_account["issuer"]
    account_1 = eth_account["deployer"]
    account_2 = eth_account["trader"]

    # Prepare balance data
    # balance = 1000000
    @staticmethod
    def create_balance_data(account, exchange_contract, token_list_contract):
        # Issue token
        args = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
        }
        token = issue_coupon_token(TestPositionCoupon.issuer, args)
        coupon_register_list(TestPositionCoupon.issuer, token, token_list_contract)
        transfer_coupon_token(
            TestPositionCoupon.issuer,
            token,
            account["account_address"],
            1000000,
        )

        return token

    # Prepare commitment data
    # balance = 1000000 - commitment, commitment = [args commitment]
    @staticmethod
    def create_commitment_data(
        account, exchange_contract, token_list_contract, commitment
    ):
        # Issue token
        token = TestPositionCoupon.create_balance_data(
            account, exchange_contract, token_list_contract
        )

        # Sell order
        agent = eth_account["agent"]
        transfer_coupon_token(account, token, exchange_contract["address"], commitment)
        ExchangeContract = Contract.get_contract(
            "IbetExchange", exchange_contract["address"]
        )
        tx_hash = ExchangeContract.functions.createOrder(
            token["address"], commitment, 10000, False, agent["account_address"]
        ).transact({"from": account["account_address"], "gas": 4000000})
        web3.eth.wait_for_transaction_receipt(tx_hash)

        return token

    # Prepare used data
    # balance = 1000000 - commitment, used = [args used]
    @staticmethod
    def create_used_data(account, exchange_contract, token_list_contract, used):
        # Issue token
        token = TestPositionCoupon.create_balance_data(
            account, exchange_contract, token_list_contract
        )

        # Used
        consume_coupon_token(account, token, used)

        return token

    # Prepare non balance data
    # balance = 0
    @staticmethod
    def create_non_balance_data(
        account, to_account, exchange_contract, token_list_contract
    ):
        # Issue token
        token = TestPositionCoupon.create_balance_data(
            account, exchange_contract, token_list_contract
        )

        # Transfer all amount
        transfer_coupon_token(account, token, to_account["account_address"], 1000000)

        return token

    @staticmethod
    def create_idx_consume(
        session: Session, token_address: str, account_address: str, amount: int
    ):
        consume = IDXConsumeCoupon()
        consume.account_address = account_address
        consume.token_address = token_address
        consume.amount = amount
        session.add(consume)
        session.commit()

    @staticmethod
    def create_idx_position(
        session: Session,
        token_address: str,
        account_address: str,
        balance: int | None = None,
        exchange_balance: int | None = None,
        exchange_commitment: int | None = None,
    ):
        if not balance and not exchange_balance and not exchange_commitment:
            return
        idx_position = IDXPosition()
        idx_position.token_address = token_address
        idx_position.account_address = account_address
        if balance:
            idx_position.balance = balance
        if exchange_balance:
            idx_position.exchange_balance = exchange_balance
        if exchange_commitment:
            idx_position.exchange_commitment = exchange_commitment
        session.merge(idx_position)
        session.commit()
        pass

    @staticmethod
    def create_idx_token(
        session: Session, token_address: str, exchange_address: str | None
    ):
        # Issue token
        idx_token = IDXCouponToken()
        idx_token.company_name = ""
        idx_token.token_address = token_address
        idx_token.owner_address = TestPositionCoupon.issuer["account_address"]
        idx_token.token_template = "IbetCoupon"
        idx_token.name = "テストクーポン"
        idx_token.symbol = "COUPON"
        idx_token.total_supply = 1000000
        idx_token.tradable_exchange = exchange_address
        idx_token.details = "クーポン詳細"
        idx_token.return_details = "リターン詳細"
        idx_token.rsa_publickey = ""
        idx_token.memo = "クーポンメモ欄"
        idx_token.expiration_date = "20191231"
        idx_token.image_url = [
            {"id": 1, "url": ""},
            {"id": 2, "url": ""},
            {"id": 3, "url": ""},
        ]
        idx_token.initial_offering_status = False
        idx_token.max_holding_quantity = 1
        idx_token.max_sell_amount = 1000
        idx_token.transferable = True
        idx_token.status = True
        idx_token.contact_information = "問い合わせ先"
        idx_token.privacy_policy = "プライバシーポリシー"
        session.add(idx_token)
        idx_token_list_item = IDXTokenListItem()
        idx_token_list_item.token_address = token_address
        idx_token_list_item.token_template = "IbetCoupon"
        idx_token_list_item.owner_address = TestPositionCoupon.issuer["account_address"]
        session.add(idx_token_list_item)
        session.commit()

    @staticmethod
    def list_token(token_address, session: Session):
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
        config.COUPON_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_5 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.list_token(token_5["address"], session)
        token_6 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.list_token(token_6["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_7 = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_7["address"], session)
        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7["address"]
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        session.add(idx_transfer)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

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
                "count": 7,
                "offset": None,
                "limit": None,
                "total": 7,
            },
            "positions": [
                {
                    "token_address": token_1["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "used": 0,
                },
                {
                    "token_address": token_4["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "used": 0,
                },
                {
                    "token_address": token_5["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 100,
                },
                {
                    "token_address": token_6["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 1000000,
                },
                {
                    "token_address": token_7["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
            ],
        }

    # <Normal_2>
    # Pagination
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.list_token(token_1["address"], session)
        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.list_token(token_2["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_3 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.list_token(token_3["address"], session)
        token_4 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.list_token(token_4["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_5 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.list_token(token_5["address"], session)
        token_6 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.list_token(token_6["address"], session)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target
        token_7 = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_7["address"], session)
        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7["address"]
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        session.add(idx_transfer)
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.list_token(token_non["address"], session)  # not target

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
                "count": 7,
                "offset": 1,
                "limit": 2,
                "total": 7,
            },
            "positions": [
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "used": 0,
                },
            ],
        }

    # <Normal_3>
    # token details
    def test_normal_3(self, client: TestClient, session: Session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.list_token(token_1["address"], session)

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
                        "token_address": token_1["address"],
                        "token_template": "IbetCoupon",
                        "owner_address": self.issuer["account_address"],
                        "company_name": "",
                        "rsa_publickey": "",
                        "name": "テストクーポン",
                        "symbol": "COUPON",
                        "total_supply": 1000000,
                        "details": "クーポン詳細",
                        "return_details": "リターン詳細",
                        "expiration_date": "20191231",
                        "memo": "クーポンメモ欄",
                        "transferable": True,
                        "status": True,
                        "initial_offering_status": False,
                        "image_url": [
                            {"id": 1, "url": ""},
                            {"id": 2, "url": ""},
                            {"id": 3, "url": ""},
                        ],
                        "max_holding_quantity": 1,
                        "max_sell_amount": 1000,
                        "contact_information": "問い合わせ先",
                        "privacy_policy": "プライバシーポリシー",
                        "tradable_exchange": config.ZERO_ADDRESS,
                    },
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
            ],
        }

    # <Normal_4>
    # List all positions
    # Indexed: <Normal_1>
    def test_normal_4(self, client: TestClient, session: Session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1["address"], session)
        self.create_idx_token(session, token_1["address"], config.ZERO_ADDRESS)

        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.create_idx_position(
            session,
            token_2["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2["address"], session)
        self.create_idx_token(session, token_2["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_3 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.create_idx_position(
            session,
            token_3["address"],
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3["address"], session)
        self.create_idx_token(session, token_3["address"], config.ZERO_ADDRESS)

        token_4 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.create_idx_position(
            session,
            token_4["address"],
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4["address"], session)
        self.create_idx_token(session, token_4["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_5 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.create_idx_position(
            session,
            token_5["address"],
            self.account_1["account_address"],
            balance=999900,
        )
        self.create_idx_consume(
            session, token_5["address"], self.account_1["account_address"], 80
        )
        self.create_idx_consume(
            session, token_5["address"], self.account_1["account_address"], 20
        )
        self.list_token(token_5["address"], session)
        self.create_idx_token(session, token_5["address"], config.ZERO_ADDRESS)

        token_6 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.create_idx_consume(
            session, token_6["address"], self.account_1["account_address"], 800000
        )
        self.create_idx_consume(
            session, token_6["address"], self.account_1["account_address"], 200000
        )
        self.list_token(token_6["address"], session)
        self.create_idx_token(session, token_6["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_7 = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_7["address"], session)
        self.create_idx_token(session, token_7["address"], config.ZERO_ADDRESS)

        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7["address"]
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        session.add(idx_transfer)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

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
                "count": 7,
                "offset": None,
                "limit": None,
                "total": 7,
            },
            "positions": [
                {
                    "token_address": token_1["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "used": 0,
                },
                {
                    "token_address": token_4["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 1000000,
                    "used": 0,
                },
                {
                    "token_address": token_5["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 100,
                },
                {
                    "token_address": token_6["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 1000000,
                },
                {
                    "token_address": token_7["address"],
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
            ],
        }

    # <Normal_5>
    # Pagination
    # Indexed: <Normal_2>
    def test_normal_5(self, client: TestClient, session: Session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True

        exchange_contract = shared_contract["IbetCouponExchange"]
        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1["address"], session)
        self.create_idx_token(session, token_1["address"], config.ZERO_ADDRESS)

        token_2 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.create_idx_position(
            session,
            token_2["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_2["address"], session)
        self.create_idx_token(session, token_2["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_3 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.create_idx_position(
            session,
            token_3["address"],
            self.account_1["account_address"],
            balance=999900,
            exchange_commitment=100,
        )
        self.list_token(token_3["address"], session)
        self.create_idx_token(session, token_3["address"], config.ZERO_ADDRESS)

        token_4 = self.create_commitment_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.create_idx_position(
            session,
            token_4["address"],
            self.account_1["account_address"],
            exchange_commitment=1000000,
        )
        self.list_token(token_4["address"], session)
        self.create_idx_token(session, token_4["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_5 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 100
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=999900,
        )
        self.create_idx_consume(
            session, token_5["address"], self.account_1["account_address"], 70
        )
        self.create_idx_consume(
            session, token_5["address"], self.account_1["account_address"], 30
        )
        self.list_token(token_5["address"], session)
        self.create_idx_token(session, token_5["address"], config.ZERO_ADDRESS)

        token_6 = self.create_used_data(
            self.account_1, exchange_contract, token_list_contract, 1000000
        )
        self.create_idx_consume(
            session, token_6["address"], self.account_1["account_address"], 700000
        )
        self.create_idx_consume(
            session, token_6["address"], self.account_1["account_address"], 300000
        )
        self.list_token(token_6["address"], session)
        self.create_idx_token(session, token_6["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

        token_7 = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_7["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_7["address"], session)
        self.create_idx_token(session, token_7["address"], config.ZERO_ADDRESS)

        idx_transfer = IDXTransfer()
        idx_transfer.transaction_hash = "tx1"
        idx_transfer.token_address = token_7["address"]
        idx_transfer.from_address = self.issuer["account_address"]
        idx_transfer.to_address = self.account_1["account_address"]
        idx_transfer.value = 100000
        idx_transfer.source_event = IDXTransferSourceEventType.TRANSFER.value
        session.add(idx_transfer)

        token_non = self.create_non_balance_data(
            self.account_1,
            self.account_2,
            {"address": config.ZERO_ADDRESS},
            token_list_contract,
        )
        self.create_idx_position(
            session,
            token_non["address"],
            self.account_2["account_address"],
            balance=1000000,
        )
        self.list_token(token_non["address"], session)  # not target
        self.create_idx_token(session, token_non["address"], config.ZERO_ADDRESS)

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
                "count": 7,
                "offset": 1,
                "limit": 2,
                "total": 7,
            },
            "positions": [
                {
                    "token_address": token_2["address"],
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
                {
                    "token_address": token_3["address"],
                    "balance": 999900,
                    "exchange_balance": 0,
                    "exchange_commitment": 100,
                    "used": 0,
                },
            ],
        }

    # <Normal_6>
    # token details
    # Indexed: <Normal_3>
    def test_normal_6(self, client: TestClient, session: Session, shared_contract):
        config.COUPON_TOKEN_ENABLED = True

        token_list_contract = shared_contract["TokenList"]

        # Prepare data
        token_1 = self.create_balance_data(
            self.account_1, {"address": config.ZERO_ADDRESS}, token_list_contract
        )
        self.create_idx_position(
            session,
            token_1["address"],
            self.account_1["account_address"],
            balance=1000000,
        )
        self.list_token(token_1["address"], session)
        self.create_idx_token(session, token_1["address"], config.ZERO_ADDRESS)

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
                        "token_address": token_1["address"],
                        "token_template": "IbetCoupon",
                        "owner_address": self.issuer["account_address"],
                        "company_name": "",
                        "rsa_publickey": "",
                        "name": "テストクーポン",
                        "symbol": "COUPON",
                        "total_supply": 1000000,
                        "details": "クーポン詳細",
                        "return_details": "リターン詳細",
                        "expiration_date": "20191231",
                        "memo": "クーポンメモ欄",
                        "transferable": True,
                        "status": True,
                        "initial_offering_status": False,
                        "image_url": [
                            {"id": 1, "url": ""},
                            {"id": 2, "url": ""},
                            {"id": 3, "url": ""},
                        ],
                        "max_holding_quantity": 1,
                        "max_sell_amount": 1000,
                        "contact_information": "問い合わせ先",
                        "privacy_policy": "プライバシーポリシー",
                        "tradable_exchange": config.ZERO_ADDRESS,
                    },
                    "balance": 1000000,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": 0,
                },
            ],
        }

    ###########################################################################
    # Error
    ###########################################################################

    # <Error_1>
    # NotSupportedError
    def test_error_1(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = False

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
            "description": f"method: GET, url: /Position/{account_address}/Coupon",
        }

    # <Error_2>
    # ParameterError: invalid account_address
    def test_error_2(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True

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
        config.COUPON_TOKEN_ENABLED = True

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
        config.COUPON_TOKEN_ENABLED = True

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
                    "msg": "Input should be a valid boolean, unable to interpret "
                    "input",
                    "type": "bool_parsing",
                },
            ],
            "message": "Invalid Parameter",
        }
