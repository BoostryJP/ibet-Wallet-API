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
import json

from app import config


class TestNodeInfoNodeInfo:
    # テスト対象API
    apiurl = '/NodeInfo/'

    # ＜正常系1＞
    # 通常参照
    def test_nodeinfo_normal_1(self, client: TestClient, session: Session):
        resp = client.get(self.apiurl)

        payment_gateway = json.load(open("app/contracts/json/PaymentGateway.json", "r"))
        personal_info = json.load(open("app/contracts/json/PersonalInfo.json", "r"))
        ibet_exchange = json.load(open("app/contracts/json/IbetExchange.json", "r"))
        ibet_escrow_json = json.load(open("app/contracts/json/IbetEscrow.json", "r"))
        ibet_security_token_escrow_json = json.load(open("app/contracts/json/IbetSecurityTokenEscrow.json", "r"))
        e2e_messaging_json = json.load(open("app/contracts/json/E2EMessaging.json", "r"))

        payment_gateway_address = config.PAYMENT_GATEWAY_CONTRACT_ADDRESS
        payment_gateway_abi = payment_gateway['abi']

        personalinfo_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
        personalinfo_abi = personal_info['abi']

        bond_exchange_address = config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        bond_exchange_abi = ibet_exchange['abi']

        membership_exchange_address = config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
        membership_exchange_abi = ibet_exchange['abi']

        coupon_exchange_address = config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
        coupon_exchange_abi = ibet_exchange['abi']

        share_exchange_address = config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
        share_exchange_abi = ibet_exchange['abi']

        ibet_escrow_address = config.IBET_ESCROW_CONTRACT_ADDRESS
        ibet_escrow_abi = ibet_escrow_json['abi']

        ibet_security_token_escrow_address = config.IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS
        ibet_security_token_escrow_abi = ibet_security_token_escrow_json['abi']

        e2e_messaging_address = config.E2E_MESSAGING_CONTRACT_ADDRESS
        e2e_messaging_abi = e2e_messaging_json['abi']

        agent_address = config.AGENT_ADDRESS

        assumed_body = {
            'payment_gateway_address': payment_gateway_address,
            'payment_gateway_abi': payment_gateway_abi,
            'personal_info_address': personalinfo_address,
            'personal_info_abi': personalinfo_abi,
            'ibet_straightbond_exchange_address': bond_exchange_address,
            'ibet_straightbond_exchange_abi': bond_exchange_abi,
            'ibet_membership_exchange_address': membership_exchange_address,
            'ibet_membership_exchange_abi': membership_exchange_abi,
            'ibet_coupon_exchange_address': coupon_exchange_address,
            'ibet_coupon_exchange_abi': coupon_exchange_abi,
            'ibet_share_exchange_address': share_exchange_address,
            'ibet_share_exchange_abi': share_exchange_abi,
            'ibet_escrow_address': ibet_escrow_address,
            'ibet_escrow_abi': ibet_escrow_abi,
            'ibet_security_token_escrow_address': ibet_security_token_escrow_address,
            'ibet_security_token_escrow_abi': ibet_security_token_escrow_abi,
            'e2e_messaging_address': e2e_messaging_address,
            'e2e_messaging_abi': e2e_messaging_abi,
            'agent_address': agent_address
        }

        assert resp.status_code == 200
        assert resp.json()['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json()['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_nodeinfo_error_1(self, client: TestClient, session: Session):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.post(
            self.apiurl, headers=headers, json=json.loads(request_body))

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "description": "method: POST, url: /NodeInfo/",
            "message": "Method Not Allowed"
        }
