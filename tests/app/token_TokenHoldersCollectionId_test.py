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

import asyncio
import uuid
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.model.db import Listing, TokenHolderBatchStatus, TokenHoldersList
from batch.indexer_Token_Holders import Processor
from tests.utils.contract import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
from tests.account_config import eth_account
from tests.contract_modules import (
    bond_lock,
    bond_transfer_to_exchange,
    bond_unlock,
    issue_bond_token,
    register_bond_list,
    register_personalinfo,
    transfer_token,
)
from tests.types import DeployedContract, SharedContract, UnitTestAccount


@pytest.fixture(scope="session")
def test_module(shared_contract: SharedContract) -> type[Processor]:
    return Processor


@pytest.fixture(scope="function")
def processor(test_module: type[Processor], session: Session) -> Processor:
    return test_module()


class TestTokenTokenHoldersCollectionId:
    """
    Test Case for token.TokenHolders
    """

    # テスト対象API
    apiurl_base = "/Token/{contract_address}/Holders/Collection/{list_id}"

    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"

    issuer = eth_account["issuer"]
    user1 = eth_account["user1"]
    user2 = eth_account["user2"]
    trader = eth_account["trader"]
    agent = eth_account["agent"]

    @staticmethod
    def issue_token_bond(
        issuer: UnitTestAccount,
        exchange_contract_address: str,
        personal_info_contract_address: str,
        token_list: DeployedContract,
    ) -> DeployedContract:
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
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
        }
        token = issue_bond_token(issuer, args)
        register_bond_list(issuer, token, token_list)

        return token

    @staticmethod
    def listing_token(token_address: str, session: Session) -> None:
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestTokenTokenHoldersCollectionId.issuer[
            "account_address"
        ]
        session.add(_listing)
        session.commit()

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # GET
    # Holders in response is empty.
    def test_normal_1(
        self,
        client: TestClient,
        shared_contract: SharedContract,
        session: Session,
        processor: Processor,
        block_number: None,
    ):
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = self.token_address
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = 1000
        session.merge(target_token_holders_list)
        session.commit()

        self.listing_token(self.token_address, session)

        # Request target API
        apiurl = self.apiurl_base.format(
            contract_address=self.token_address,
            list_id=target_token_holders_list.list_id,
        )

        resp = client.get(apiurl)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {
            "status": TokenHolderBatchStatus.PENDING.value,
            "holders": [],
        }

    # Normal_2
    # GET
    # Holders in response is filled after holders data is generated properly by batch.
    def test_normal_2(
        self,
        client: TestClient,
        shared_contract: SharedContract,
        session: Session,
        processor: Processor,
        block_number: None,
    ):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer,
            escrow_contract.address,
            personal_info_contract["address"],
            token_list_contract,
        )

        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.user1, personal_info_contract)

        # Transfer
        bond_transfer_to_exchange(
            self.issuer, {"address": escrow_contract.address}, token, 10000
        )
        transfer_token(
            token_contract,
            self.issuer["account_address"],
            self.trader["account_address"],
            30000,
        )
        transfer_token(
            token_contract,
            self.issuer["account_address"],
            self.user1["account_address"],
            50000,
        )
        bond_transfer_to_exchange(
            self.user1, {"address": escrow_contract.address}, token, 30000
        )
        bond_lock(self.trader, token, self.user1["account_address"], 2000)
        bond_lock(self.trader, token, self.issuer["account_address"], 1000)
        bond_unlock(
            self.user1,
            token,
            self.trader["account_address"],
            self.user1["account_address"],
            1000,
        )

        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = token["address"]
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = web3.eth.block_number
        session.merge(target_token_holders_list)
        session.commit()

        with mock.patch(
            "batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS",
            token_list_contract["address"],
        ):
            asyncio.run(processor.collect())

        # Request target API
        apiurl = self.apiurl_base.format(
            contract_address=token["address"], list_id=target_token_holders_list.list_id
        )
        resp = client.get(apiurl)

        # Assertion
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"]["status"] == TokenHolderBatchStatus.DONE.value

        assert len(resp.json()["data"]["holders"]) == 2

        for holder in resp.json()["data"]["holders"]:
            if holder["account_address"] == self.trader["account_address"]:
                assert holder == {
                    "account_address": self.trader["account_address"],
                    "hold_balance": 27000,
                    "locked_balance": 2000,
                }
            elif holder["account_address"] == self.user1["account_address"]:
                assert holder == {
                    "account_address": self.user1["account_address"],
                    "hold_balance": 51000,
                    "locked_balance": 0,
                }

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 400: Invalid Parameter Error
    # Invalid contract address
    def test_error_1(self, client: TestClient, session: Session):
        list_id = str(uuid.uuid4())
        apiurl = self.apiurl_base.format(contract_address="0xabcd", list_id=list_id)

        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["path", "token_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0xabcd",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2
    # 400: Invalid Parameter Error
    # Invalid list_id
    def test_error_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(
            contract_address=config.ZERO_ADDRESS, list_id="some_id"
        )
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {
                        "error": "invalid character: expected an optional "
                        "prefix of `urn:uuid:` followed by "
                        "[0-9a-fA-F-], found `s` at 1"
                    },
                    "input": "some_id",
                    "loc": ["path", "list_id"],
                    "msg": "Input should be a valid UUID, invalid character: "
                    "expected an optional prefix of `urn:uuid:` followed "
                    "by [0-9a-fA-F-], found `s` at 1",
                    "type": "uuid_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3
    # 404: Data Not Exists Error
    # There is no record with given list_id.
    def test_error_3(self, client: TestClient, session: Session):
        self.listing_token(self.token_address, session)
        list_id = str(uuid.uuid4())
        apiurl = self.apiurl_base.format(
            contract_address=self.token_address, list_id=list_id
        )
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "list_id: " + list_id,
        }
