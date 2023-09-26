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
from web3 import Web3

from app import config
from tests.account_config import eth_account


class TestEthGetTransactionCount:
    # テスト対象API
    apiurl_base = "/Eth/TransactionCount/"

    ###########################################################################
    # Normal
    ###########################################################################

    # ＜正常系1＞
    # トランザクション未実行のアドレス
    # -> nonce = 0
    def test_transactioncount_normal_1(self, client: TestClient, session: Session):
        # 任意のアドレス
        some_account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"

        apiurl = self.apiurl_base + some_account_address
        resp = client.get(apiurl)

        assumed_body = {"chainid": "2017", "gasprice": 0, "nonce": 0}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2＞
    # トランザクション実行済みのアドレス
    # -> nonce = （ブロックを直接参照した情報と一致）
    def test_transactioncount_normal_2(self, client: TestClient, session: Session):
        # deployerのアドレス
        eth_address = eth_account["deployer"]["account_address"]

        apiurl = self.apiurl_base + eth_address
        resp = client.get(apiurl)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        nonce = web3.eth.get_transaction_count(eth_address)

        assumed_body = {"chainid": "2017", "gasprice": 0, "nonce": nonce}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系3＞
    # block_identifier = "pending"
    def test_transactioncount_normal_3(self, client: TestClient, session: Session):
        # deployerのアドレス
        eth_address = eth_account["deployer"]["account_address"]

        apiurl = self.apiurl_base + eth_address
        query_string = "block_identifier=pending"
        resp = client.get(apiurl, params=query_string)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        nonce = web3.eth.get_transaction_count(eth_address)

        assumed_body = {"chainid": "2017", "gasprice": 0, "nonce": nonce}

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_transactioncount_error_1(self, client: TestClient, session: Session):
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})

        resp = client.post(self.apiurl_base, headers=headers, params=request_body)

        assert resp.status_code == 404

    # ＜エラー系2＞
    # addressのフォーマットが正しくない
    # -> 400エラー（InvalidParameterError）
    def test_transactioncount_error_2(self, client: TestClient, session: Session):
        some_account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9"  # アドレス長が短い

        apiurl = self.apiurl_base + some_account_address
        resp = client.get(apiurl)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {"code": 88, "message": "Invalid Parameter"}

    # ＜エラー系3＞
    # addressが未設定
    # -> 400エラー
    def test_transactioncount_error_3(self, client: TestClient, session: Session):
        apiurl = self.apiurl_base
        resp = client.get(apiurl)

        assert resp.status_code == 404

    # ＜エラー系4＞
    # トランザクション実行済みのアドレス
    # block_identifier に取り得る値以外
    # -> 400
    def test_transactioncount_error_4(self, client: TestClient, session: Session):
        # 任意のアドレス
        some_account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"

        apiurl = self.apiurl_base + some_account_address
        query_string = "block_identifier=hoge"
        resp = client.get(apiurl, params=query_string)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"enum_values": ["latest", "earliest", "pending"]},
                    "loc": ["query", "block_identifier"],
                    "msg": "value is not a valid enumeration member; permitted: "
                    "'latest', 'earliest', 'pending'",
                    "type": "type_error.enum",
                }
            ],
            "message": "Invalid Parameter",
        }
