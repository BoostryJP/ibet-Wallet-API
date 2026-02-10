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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config


class TestNodeInfoNodeInfo:
    # Test API
    apiurl = "/NodeInfo"

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    def test_nodeinfo_normal_1(self, client: TestClient, session: Session):
        resp = client.get(self.apiurl)

        personal_info = json.load(open("app/contracts/json/PersonalInfo.json", "r"))
        ibet_escrow_json = json.load(open("app/contracts/json/IbetEscrow.json", "r"))
        ibet_security_token_escrow_json = json.load(
            open("app/contracts/json/IbetSecurityTokenEscrow.json", "r")
        )
        ibet_security_token_dvp_json = json.load(
            open("app/contracts/json/IbetSecurityTokenDVP.json", "r")
        )
        e2e_messaging_json = json.load(
            open("app/contracts/json/E2EMessaging.json", "r")
        )

        personalinfo_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
        personalinfo_abi = personal_info["abi"]

        ibet_escrow_address = config.IBET_ESCROW_CONTRACT_ADDRESS
        ibet_escrow_abi = ibet_escrow_json["abi"]

        ibet_security_token_escrow_address = (
            config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS
        )
        ibet_security_token_escrow_abi = ibet_security_token_escrow_json["abi"]

        ibet_security_token_dvp_address = (
            config.IBET_SECURITY_TOKEN_DVP_CONTRACT_ADDRESS
        )
        ibet_security_token_dvp_abi = ibet_security_token_dvp_json["abi"]

        e2e_messaging_address = config.E2E_MESSAGING_CONTRACT_ADDRESS
        e2e_messaging_abi = e2e_messaging_json["abi"]

        assumed_body = {
            "personal_info_address": personalinfo_address,
            "personal_info_abi": personalinfo_abi,
            "ibet_escrow_address": ibet_escrow_address,
            "ibet_escrow_abi": ibet_escrow_abi,
            "ibet_security_token_escrow_address": ibet_security_token_escrow_address,
            "ibet_security_token_escrow_abi": ibet_security_token_escrow_abi,
            "ibet_security_token_dvp_address": ibet_security_token_dvp_address,
            "ibet_security_token_dvp_abi": ibet_security_token_dvp_abi,
            "e2e_messaging_address": e2e_messaging_address,
            "e2e_messaging_abi": e2e_messaging_abi,
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # Invalid HTTP method: 405
    def test_nodeinfo_error_1(self, client: TestClient, session: Session):
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})

        resp = client.post(self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "description": "method: POST, url: /NodeInfo",
            "message": "Method Not Allowed",
        }
