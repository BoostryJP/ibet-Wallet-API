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
import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest import mock

from web3.middleware import geth_poa_middleware
from web3 import Web3
from app import config
from app.contracts import Contract
from app.model.db import TokenHolderBatchStatus, TokenHoldersList, Listing
from batch.indexer_Token_Holders import Processor

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)
from sqlalchemy.orm import Session

from tests.account_config import eth_account
from tests.contract_modules import (
    issue_bond_token,
    register_bond_list,
    transfer_token,
    bond_transfer_to_exchange,
    register_personalinfo,
)


@pytest.fixture(scope="session")
def test_module(shared_contract):
    return Processor


@pytest.fixture(scope="function")
def processor(test_module, session):
    processor = test_module()
    return processor


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
    def listing_token(token_address, session):
        _listing = Listing()
        _listing.token_address = token_address
        _listing.is_public = True
        _listing.max_holding_quantity = 1000000
        _listing.max_sell_amount = 1000000
        _listing.owner_address = TestTokenTokenHoldersCollectionId.issuer["account_address"]
        session.add(_listing)
        session.commit()

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # GET
    # Holders in response is empty.
    def test_normal_1(self, client: TestClient, shared_contract, session: Session, processor: Processor, block_number: None):
        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = self.token_address
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = 1000
        session.merge(target_token_holders_list)
        session.commit()

        self.listing_token(self.token_address, session)

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=self.token_address, list_id=target_token_holders_list.list_id)

        resp = client.get(apiurl)

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {"status": TokenHolderBatchStatus.PENDING.value, "holders": []}

    # Normal_2
    # GET
    # Holders in response is filled after holders data is generated properly by batch.
    def test_normal_2(self, client: TestClient, shared_contract, session: Session, processor: Processor, block_number: None):
        # Issue Token
        token_list_contract = shared_contract["TokenList"]
        escrow_contract = shared_contract["IbetSecurityTokenEscrow"]
        personal_info_contract = shared_contract["PersonalInfo"]
        token = self.issue_token_bond(
            self.issuer, escrow_contract.address, personal_info_contract["address"], token_list_contract
        )

        self.listing_token(token["address"], session)
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list_contract["address"]
        token_contract = Contract.get_contract("IbetStraightBond", token["address"])
        register_personalinfo(self.trader, personal_info_contract)
        register_personalinfo(self.user1, personal_info_contract)

        # Transfer
        bond_transfer_to_exchange(self.issuer, {"address": escrow_contract.address}, token, 10000)
        transfer_token(token_contract, self.issuer["account_address"], self.trader["account_address"], 30000)
        transfer_token(token_contract, self.issuer["account_address"], self.user1["account_address"], 50000)
        bond_transfer_to_exchange(self.user1, {"address": escrow_contract.address}, token, 30000)

        target_token_holders_list = TokenHoldersList()
        target_token_holders_list.token_address = token["address"]
        target_token_holders_list.list_id = str(uuid.uuid4())
        target_token_holders_list.batch_status = TokenHolderBatchStatus.PENDING.value
        target_token_holders_list.block_number = web3.eth.block_number
        session.merge(target_token_holders_list)
        session.commit()

        with mock.patch("batch.indexer_Token_Holders.TOKEN_LIST_CONTRACT_ADDRESS", token_list_contract["address"]):
            processor.collect()

        # Request target API
        apiurl = self.apiurl_base.format(contract_address=token["address"], list_id=target_token_holders_list.list_id)
        resp = client.get(apiurl)

        holders = [{
            "account_address": self.trader["account_address"],
            "hold_balance": 30000
        }, {
            "account_address": self.user1["account_address"],
            "hold_balance": 50000
        }]

        sorted_holders = sorted(holders, key=lambda x: x['account_address'])

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == {"status": TokenHolderBatchStatus.DONE.value, "holders": sorted_holders}

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
        assert resp.json()["meta"] == {"code": 88, "message": "Invalid Parameter", "description": "invalid contract_address"}

    # Error_2
    # 400: Invalid Parameter Error
    # Invalid list_id
    def test_error_2(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base.format(contract_address=config.ZERO_ADDRESS, list_id="some_id")
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 1,
            "description": [
                {
                    "loc": ["path", "list_id"],
                    "msg": "value is not a valid uuid",
                    "type": "type_error.uuid"
                }
            ],
            "message": "Request Validation Error"
        }

    # Error_3
    # 404: Data Not Exists Error
    # There is no record with given list_id.
    def test_error_3(self, client: TestClient, session: Session):
        self.listing_token(self.token_address, session)
        list_id = str(uuid.uuid4())
        apiurl = self.apiurl_base.format(contract_address=self.token_address, list_id=list_id)
        query_string = ""
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {"code": 30, "message": "Data Not Exists", "description": "list_id: " + list_id}
