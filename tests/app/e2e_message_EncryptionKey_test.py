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
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract
from tests.account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestE2EMessageEncryptionKey:

    # Test API
    apiurl = "/E2EMessage/EncryptionKey/{account_address}"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    def test_normal_1(self, client: TestClient, session: Session, shared_contract):
        user1 = eth_account["user1"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=e2e_messaging_contract.address
        )
        e2e_messaging_contract.functions.setPublicKey(
            "test_key",
            "test_key_type"
        ).transact({
            "from": user1
        })

        # request target API
        resp = client.get(
            self.apiurl.format(account_address=user1)
        )

        # assertion
        assumed_body = {
            "key": "test_key",
            "key_type": "test_key_type"
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {
            "code": 200,
            "message": "OK"
        }
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # InvalidParameterError
    # invalid account_address
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        user1 = eth_account["user1"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # prepare data
        e2e_messaging_contract = Contract.get_contract(
            contract_name="E2EMessaging",
            address=e2e_messaging_contract.address
        )
        e2e_messaging_contract.functions.setPublicKey(
            "test_key",
            "test_key_type"
        ).transact({
            "from": user1
        })

        # request target API
        resp = client.get(
            self.apiurl.format(account_address=user1[:-1])
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid account_address"
        }

    # Error_2
    # DataNotExistsError
    # encryption key is not registered
    def test_error_2(self, client: TestClient, session: Session, shared_contract):
        user = eth_account["deployer"]
        e2e_messaging_contract = shared_contract["E2EMessaging"]
        config.E2E_MESSAGING_CONTRACT_ADDRESS = e2e_messaging_contract.address

        # request target API
        resp = client.get(
            self.apiurl.format(account_address=user)
        )

        # assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": f"account_address: {user}"
        }
