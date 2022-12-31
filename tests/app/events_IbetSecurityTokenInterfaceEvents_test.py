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
from unittest.mock import ANY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from app.model.db import Listing
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    issue_share_token,
    register_share_list,
    register_personalinfo,
    transfer_token,
    bond_transfer_to_exchange,
    bond_issue_from,
    bond_redeem_from,
    bond_lock,
    bond_set_transfer_approval_required,
    bond_unlock,
    finish_security_token_escrow,
    get_latest_security_escrow_id,
    create_security_token_escrow,
    approve_transfer_security_token_escrow,
    bond_approve_transfer,
    bond_cancel_transfer,
    bond_apply_for_transfer
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestEventsIbetSecurityTokenInterface:
    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    # Test API
    apiurl = "/Events/IbetSecurityTokenInterface/{token_address}"

    @staticmethod
    def listing_token(token_address, session):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestEventsIbetSecurityTokenInterface.issuer["account_address"]
        session.add(_listing)
        session.commit()

    @staticmethod
    def issue_token_bond(issuer, exchange_contract_address, personal_info_contract_address, token_list):
        # Issue token
        args = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange_contract_address,
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
            "personalInfoAddress": personal_info_contract_address,
            "transferable": True,
            "isRedeemed": False,
        }
        token = issue_bond_token(issuer, args)
        register_bond_list(issuer, token, token_list)

        return token

    @staticmethod
    def issue_token_share(issuer, exchange_contract_address, personal_info_contract_address, token_list):
        # Issue token
        args = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange_contract_address,
            "personalInfoAddress": personal_info_contract_address,
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
        token = issue_share_token(issuer, args)
        register_share_list(issuer, token, token_list)

        return token

    # Setup Events Data
    # - Transfer
    # - ApplyForTransfer
    # - CancelForTransfer
    # - ApproveTransfer
    # - Escrow
    #   - CreateEscrow
    #   - FinishEscrow
    #   - ApproveTransfer
    # - Lock
    # - Unlock
    def setup_data(self, session: Session, shared_contract):
        token_list_contract = shared_contract["TokenList"]
        personal_info_contract = shared_contract["PersonalInfo"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]

        # Issuer issues bond token.
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )
        self.listing_token(token["address"], session)
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])

        # User1 and trader must register personal information before they receive token.
        register_personalinfo(self.user1, personal_info_contract)
        register_personalinfo(self.trader, personal_info_contract)

        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 20000)
        bond_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 10000)
        # user1: 20000 trader: 0

        # Issuer transfers issued token to user1 and trader.
        bond_set_transfer_approval_required(self.issuer, token, True)
        bond_apply_for_transfer(self.issuer, token, self.user1, 10000, "to user1#1")
        bond_apply_for_transfer(self.issuer, token, self.trader, 10000, "to trader#1")

        bond_cancel_transfer(self.issuer, token, 0, "to user1#1")
        bond_approve_transfer(self.issuer, token, 1, "to trader#1")
        # user1: 20000 trader: 10000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            7000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        approve_transfer_security_token_escrow(self.issuer, {"address": escrow_contract.address}, _latest_security_escrow_id, "")
        # user1: 13000 trader: 17000

        create_security_token_escrow(
            self.user1,
            {"address": escrow_contract.address},
            token,
            self.trader["account_address"],
            self.agent["account_address"],
            2000,
        )
        _latest_security_escrow_id = get_latest_security_escrow_id({"address": escrow_contract.address})
        finish_security_token_escrow(self.agent, {"address": escrow_contract.address}, _latest_security_escrow_id)
        # user1: 13000 trader: 17000

        bond_lock(self.trader, token, self.issuer["account_address"], 3000)
        # user1: 13000 trader: 17000

        bond_unlock(self.issuer, token, self.trader["account_address"], self.user1["account_address"], 2000)
        # user1: 15000 trader: 15000

        bond_set_transfer_approval_required(self.issuer, token, False)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 100000)
        # user1: 115000 trader: 15000

        bond_issue_from(self.issuer, token, self.issuer["account_address"], 40000)
        bond_redeem_from(self.issuer, token, self.user1["account_address"], 10000)
        # user1: 105000 trader: 15000

        bond_issue_from(self.issuer, token, self.trader["account_address"], 30000)
        bond_redeem_from(self.issuer, token, self.issuer["account_address"], 10000)
        # user1: 115000 trader: 45000

        self.token_address = token["address"]
        self.latest_block_number = web3.eth.block_number

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1_1
    # No event
    def test_normal_1_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": self.latest_block_number + 1,
                "to_block": self.latest_block_number + 1
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == []

    # Normal_1_2
    # event = All
    def test_normal_1_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ChangeTransferApprovalRequired",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ApplyForTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ApplyForTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "CancelTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ApproveTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Lock",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Unlock",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ChangeTransferApprovalRequired",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Issue",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Redeem",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Issue",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Redeem",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_1_3
    # event = All(argument_filter: lockAddress)
    def test_normal_1_3(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "argument_filters": json.dumps(
                    {
                        "lockAddress": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ChangeTransferApprovalRequired",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ApplyForTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ApplyForTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "CancelTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ApproveTransfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Lock",
                "args": {
                    "accountAddress": ANY,
                    "data": "",
                    "lockAddress": self.issuer["account_address"],
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Unlock",
                "args": {
                    "accountAddress": ANY,
                    "data": "",
                    "lockAddress": self.issuer["account_address"],
                    "recipientAddress": ANY,
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "ChangeTransferApprovalRequired",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_2_1
    # event = Transfer
    def test_normal_2_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Transfer"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": ANY,
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_2_2
    # event = Transfer(argument_filter: from)
    def test_normal_2_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Transfer",
                "argument_filters": json.dumps(
                    {
                        "from": self.user1["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Transfer",
                "args": {
                    "from": self.user1["account_address"],
                    "to": ANY,
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_2_3
    # event = Transfer(argument_filter: from)
    def test_normal_2_3(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Transfer",
                "argument_filters": json.dumps(
                    {
                        "to": self.user1["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Transfer",
                "args": {
                    "from": ANY,
                    "to": self.user1["account_address"],
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Transfer",
                "args": {
                    "from": ANY,
                    "to": self.user1["account_address"],
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_3_1
    # event = Issue
    def test_normal_3_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Issue"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.issuer["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.trader["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_3_2
    # event = Issue(argument_filter: from)
    def test_normal_3_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Issue",
                "argument_filters": json.dumps(
                    {
                        "from": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.issuer["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.trader["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_3_3
    # event = Issue(argument_filter: targetAddress)
    def test_normal_3_3(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Issue",
                "argument_filters": json.dumps(
                    {
                        "targetAddress": self.trader["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.trader["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_3_4
    # event = Issue(argument_filter: lockAddress)
    def test_normal_3_4(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Issue",
                "argument_filters": json.dumps(
                    {
                        "lockAddress": config.ZERO_ADDRESS
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": config.ZERO_ADDRESS,
                    "targetAddress": ANY,
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Issue",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": config.ZERO_ADDRESS,
                    "targetAddress": ANY,
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_4_1
    # event = Redeem
    def test_normal_4_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Redeem"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Redeem",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.user1["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Redeem",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.issuer["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_4_2
    # event = Redeem(argument_filter: from)
    def test_normal_4_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Redeem",
                "argument_filters": json.dumps(
                    {
                        "targetAddress": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Redeem",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": config.ZERO_ADDRESS,
                    "targetAddress": self.issuer["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_4_3
    # event = Redeem(argument_filter: targetAddress)
    def test_normal_4_3(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Redeem",
                "argument_filters": json.dumps(
                    {
                        "targetAddress": self.user1["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Redeem",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": ANY,
                    "targetAddress": self.user1["account_address"],
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_4_4
    # event = Redeem(argument_filter: lockAddress)
    def test_normal_4_4(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Redeem",
                "argument_filters": json.dumps(
                    {
                        "lockAddress": config.ZERO_ADDRESS
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Redeem",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": config.ZERO_ADDRESS,
                    "targetAddress": ANY,
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            },
            {
                "event": "Redeem",
                "args": {
                    "from": self.issuer["account_address"],
                    "lockAddress": config.ZERO_ADDRESS,
                    "targetAddress": ANY,
                    "amount": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_5_1
    # event = Lock
    def test_normal_5_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Lock"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Lock",
                "args": {
                    "accountAddress": self.trader["account_address"],
                    "lockAddress": self.issuer["account_address"],
                    "data": "",
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_5_2
    # event = Lock(argument_filter: accountAddress)
    def test_normal_5_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Lock",
                "argument_filters": json.dumps(
                    {
                        "accountAddress": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == []

    # Normal_5_3
    # event = Lock(argument_filter: lockAddress)
    def test_normal_5_3(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Lock",
                "argument_filters": json.dumps(
                    {
                        "lockAddress": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Lock",
                "args": {
                    "accountAddress": self.trader["account_address"],
                    "lockAddress": self.issuer["account_address"],
                    "data": "",
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_6_1
    # event = Unlock
    def test_normal_6_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Unlock"
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Unlock",
                "args": {
                    "accountAddress": self.trader["account_address"],
                    "lockAddress": self.issuer["account_address"],
                    "recipientAddress": self.user1["account_address"],
                    "data": "",
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    # Normal_6_2
    # event = Unlock(argument_filter: accountAddress)
    def test_normal_6_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Unlock",
                "argument_filters": json.dumps(
                    {
                        "accountAddress": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == []

    # Normal_6_3
    # event = Unlock(argument_filter: lockAddress)
    def test_normal_6_3(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "Unlock",
                "argument_filters": json.dumps(
                    {
                        "lockAddress": self.issuer["account_address"]
                    }
                )
            }
        )

        # assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == [
            {
                "event": "Unlock",
                "args": {
                    "accountAddress": self.trader["account_address"],
                    "lockAddress": self.issuer["account_address"],
                    "recipientAddress": self.user1["account_address"],
                    "data": "",
                    "value": ANY
                },
                "transaction_hash": ANY,
                "block_number": ANY,
                "block_timestamp": ANY,
                "log_index": ANY
            }
        ]

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # null value not allowed
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={}
        )

        # request target API
        resp = client.get(
            self.apiurl,
            params={}
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["query", "from_block"],
                    "msg": "field required",
                    "type": "value_error.missing"
                },
                {
                    "loc": ["query", "to_block"],
                    "msg": "field required",
                    "type": "value_error.missing"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_2
    # InvalidParameterError
    # from_block, to_block: min value
    def test_error_2(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": 0,
                "to_block": 0
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"limit_value": 1},
                    "loc": ["query", "from_block"],
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                },
                {
                    "ctx": {"limit_value": 1},
                    "loc": ["query", "to_block"],
                    "msg": "ensure this value is greater than or equal to 1",
                    "type": "value_error.number.not_ge"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_3_1
    # InvalidParameterError
    # event: unallowed value
    def test_error_3_1(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": self.latest_block_number,
                "event": "invalid"
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {
                        "enum_values": [
                            "Allot",
                            "ApplyForOffering",
                            "ApplyForTransfer",
                            "ApproveTransfer",
                            "CancelTransfer",
                            "ChangeOfferingStatus",
                            "ChangeStatus",
                            "ChangeTransferApprovalRequired",
                            "Issue",
                            "Lock",
                            "Redeem",
                            "Transfer",
                            "Unlock"
                        ]
                    },
                    "loc": ["query", "event"],
                    "msg": 'value is not a valid enumeration member; permitted: '
                         "'Allot', 'ApplyForOffering', 'ApplyForTransfer', "
                         "'ApproveTransfer', 'CancelTransfer', "
                         "'ChangeOfferingStatus', 'ChangeStatus', "
                         "'ChangeTransferApprovalRequired', 'Issue', 'Lock', "
                         "'Redeem', 'Transfer', 'Unlock'",
                    "type": "type_error.enum"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_4
    # InvalidParameterError
    # to_block must be greater than or equal to the from_block
    def test_error_4(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": self.latest_block_number,
                "to_block": self.latest_block_number-1
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "loc": ["__root__"],
                    "msg": "to_block must be greater than or equal to the from_block",
                    "type": "value_error"
                }
            ],
            "message": "Invalid Parameter"
        }

    # Error_5
    # RequestBlockRangeLimitExceededError
    # block range must be less than or equal to 10000
    def test_error_5(self, client: TestClient, session: Session, shared_contract):
        current_block_number = web3.eth.block_number
        self.setup_data(session, shared_contract)

        # request target API
        resp = client.get(
            self.apiurl.format(token_address=self.token_address),
            params={
                "from_block": current_block_number,
                "to_block": current_block_number + 10001
            }
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 31,
            "description": "Search request range is over the limit",
            "message": "Request Block Range Limit Exceeded"
        }
