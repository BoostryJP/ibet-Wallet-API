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
import sys

from eth_utils import to_checksum_address
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import config
from app.model.db import AgreementStatus, IDXAgreement as Agreement, IDXOrder as Order
from tests.account_config import eth_account


class TestDEXMarketCouponOrderBook:
    # テスト対象API
    apiurl = "/DEX/Market/OrderBook/Coupon"

    def setup_method(self):
        # 環境変数設定
        config.AGENT_ADDRESS = eth_account["agent"]["account_address"]

    ###########################################################################
    # Normal
    ###########################################################################

    # ＜正常系1-1-1＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> リスト1件が返却
    def test_normal_1_1_1(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 1,
                "price": 1000,
                "amount": 100,
                "account_address": account_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系1-1-2＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) アカウントアドレスの指定なし
    #
    # -> リスト1件が返却
    def test_normal_1_1_2(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 1,
                "price": 1000,
                "amount": 100,
                "account_address": account_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系1-2＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と異なるトークンアドレス　※
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_normal_1_2(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系1-3＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 売り注文　※
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_normal_1_3(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系1-4＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文と同一のアカウントアドレス　※
    #
    # -> ゼロ件リストが返却
    def test_normal_1_4(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": account_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系1-5＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 限界値
    def test_normal_1_5(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.id = sys.maxsize
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = sys.maxsize
        order.unique_order_id = exchange_address + "_" + str(sys.maxsize)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = sys.maxsize
        order.amount = sys.maxsize
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": sys.maxsize,
                "price": sys.maxsize,
                "amount": sys.maxsize,
                "account_address": account_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系1-6＞
    # 未約定＆未キャンセルの売り注文が1件存在（ただし、他のExchangeのデータ）
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_normal_1_6(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43"
        order.order_id = 1
        order.unique_order_id = (
            "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43" + "_" + str(1)
        )
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2-1＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 売り注文
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> リスト1件が返却
    def test_normal_2_1(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 1,
                "price": 1000,
                "amount": 100,
                "account_address": account_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2-2＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と異なるトークンアドレス　※
    #   2) 売り注文
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_normal_2_2(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2-3＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 買い注文　※
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_normal_2_3(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2-4＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 売り注文
    #   3) 買い注文と同一のアカウントアドレス　※
    #
    # -> ゼロ件リストが返却
    def test_normal_2_4(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": account_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2-5＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 限界値
    def test_normal_2_5(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.id = sys.maxsize
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = sys.maxsize
        order.unique_order_id = exchange_address + "_" + str(sys.maxsize)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = sys.maxsize
        order.amount = sys.maxsize
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": sys.maxsize,
                "price": sys.maxsize,
                "amount": sys.maxsize,
                "account_address": account_address,
            }
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系2-6＞
    # 未約定＆未キャンセルの買い注文が1件存在（ただし、他のExchangeのデータ）
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 売り注文
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_normal_2_6(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43"
        order.order_id = 1
        order.unique_order_id = (
            "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43" + "_" + str(1)
        )
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系3-1＞
    # 未約定＆未キャンセルの売り注文が複数件存在
    # -> リストのソート順が価格の昇順
    def test_normal_3_1(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 2
        order.unique_order_id = exchange_address + "_" + str(2)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 999
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 2,
                "price": 999,
                "amount": 100,
                "account_address": account_address,
            },
            {
                "exchange_address": exchange_address,
                "order_id": 1,
                "price": 1000,
                "amount": 100,
                "account_address": account_address,
            },
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系3-2＞
    # 未約定＆未キャンセルの買い注文が複数件存在
    # -> リストのソート順が価格の降順
    def test_normal_3_2(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account["agent"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 2
        order.unique_order_id = exchange_address + "_" + str(2)
        order.account_address = account_address
        order.counterpart_address = ""
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1001
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": agent_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 2,
                "price": 1001,
                "amount": 100,
                "account_address": account_address,
            },
            {
                "exchange_address": exchange_address,
                "order_id": 1,
                "price": 1000,
                "amount": 100,
                "account_address": account_address,
            },
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系4-1＞
    # 約定済み（※部分約定,約定否認含む）の売り注文が複数存在:アカウントアドレス指定
    #  -> 未約定のOrderBookリストが返却される
    def test_normal_4_1(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616",  # 注文者2
        ]
        agent_address = eth_account["agent"]["account_address"]

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + "_" + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 2000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 2
        order.unique_order_id = exchange_address + "_" + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 3000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 3
        order.unique_order_id = exchange_address + "_" + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 6000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = 1
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": account_addresses[0],
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 2,
                "price": 3000,
                "amount": 50,
                "account_address": account_addresses[2],
            },
            {
                "exchange_address": exchange_address,
                "order_id": 3,
                "price": 6000,
                "amount": 70,
                "account_address": account_addresses[1],
            },
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系4-2＞
    # 約定済み（※部分約定,約定否認含む）の買い注文が複数存在:アカウントアドレス指定
    #  -> 未約定のOrderBookリストが返却される
    def test_normal_4_2(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616",  # 注文者2
        ]
        agent_address = eth_account["agent"]["account_address"]

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + "_" + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 2000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 2
        order.unique_order_id = exchange_address + "_" + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 3000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 3
        order.unique_order_id = exchange_address + "_" + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 6000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = 1
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
            "account_address": account_addresses[0],
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 3,
                "price": 6000,
                "amount": 70,
                "account_address": account_addresses[1],
            },
            {
                "exchange_address": exchange_address,
                "order_id": 2,
                "price": 3000,
                "amount": 50,
                "account_address": account_addresses[2],
            },
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系4-3＞
    # 約定済み（※部分約定、約定取消含む）の売り注文が複数存在:アカウントアドレス指定なし
    #  -> 未約定のOrderBookリストが返却される
    def test_normal_4_3(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616",  # 注文者2
        ]
        agent_address = eth_account["agent"]["account_address"]

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + "_" + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 2000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 2
        order.unique_order_id = exchange_address + "_" + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 3000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 3
        order.unique_order_id = exchange_address + "_" + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 6000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = 1
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 0,
                "price": 1000,
                "amount": 100,
                "account_address": account_addresses[0],
            },
            {
                "exchange_address": exchange_address,
                "order_id": 2,
                "price": 3000,
                "amount": 50,
                "account_address": account_addresses[2],
            },
            {
                "exchange_address": exchange_address,
                "order_id": 3,
                "price": 6000,
                "amount": 70,
                "account_address": account_addresses[1],
            },
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系4-4＞
    # 約定済み（※部分約定、約定取消含む）の買い注文が複数存在:アカウントアドレス指定なし
    #  -> 未約定のOrderBookリストが返却される
    def test_normal_4_4(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616",  # 注文者2
        ]
        agent_address = eth_account["agent"]["account_address"]

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + "_" + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 2000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 2
        order.unique_order_id = exchange_address + "_" + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 3000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 3
        order.unique_order_id = exchange_address + "_" + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ""
        order.is_buy = True
        order.price = 6000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # Agreementの情報を挿入
        agreement = Agreement()
        agreement.order_id = 1
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + "_" + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = [
            {
                "exchange_address": exchange_address,
                "order_id": 3,
                "price": 6000,
                "amount": 70,
                "account_address": account_addresses[1],
            },
            {
                "exchange_address": exchange_address,
                "order_id": 2,
                "price": 3000,
                "amount": 50,
                "account_address": account_addresses[2],
            },
            {
                "exchange_address": exchange_address,
                "order_id": 0,
                "price": 1000,
                "amount": 100,
                "account_address": account_addresses[0],
            },
        ]

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    # ＜正常系5＞
    # 異なる exchange_agent_address
    def test_normal_5(self, client: TestClient, session: Session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = to_checksum_address(
            "0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address_1 = eth_account["agent"]["account_address"]
        agent_address_2 = eth_account["user1"]["account_address"]

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + "_" + str(1)
        order.account_address = account_address
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address_1
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address_2,
            "order_type": "buy",
        }
        resp = client.get(self.apiurl, params=request_params)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert resp.json()["data"] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # field required
    # Invalid Parameter
    def test_error_1(self, client: TestClient, session: Session):
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address

        resp = client.get(self.apiurl, params={})

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": None,
                    "loc": ["query", "token_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
                    "loc": ["query", "exchange_agent_address"],
                    "msg": "Field required",
                    "type": "missing",
                },
                {
                    "input": None,
                    "loc": ["query", "order_type"],
                    "msg": "Field required",
                    "type": "missing",
                },
            ],
            "message": "Invalid Parameter",
        }

    # Error_2_1
    # token_address is not a valid address
    # Invalid Parameter
    def test_error_2_1(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレスが短い
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        agent_address = eth_account["agent"]["account_address"]
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": account_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "token_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": token_address,
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2_2
    # token_address is not a valid address
    # Invalid Parameter
    def test_error_2_2(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        agent_address = eth_account["agent"]["account_address"][:-1]  # アドレスが短い
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": account_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "exchange_agent_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": agent_address,
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2_3
    # account_address is not a valid address
    # Invalid Parameter
    def test_error_2_3(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        agent_address = eth_account["agent"]["account_address"]
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buy",
            "account_address": account_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "account_address"],
                    "msg": "Value error, Invalid ethereum address",
                    "input": account_address,
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_3
    # order_type: value is not a valid enumeration member
    # Invalid Parameter
    def test_error_3(self, client: TestClient, session: Session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        agent_address = eth_account["agent"]["account_address"]
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "buyyyyy",
            "account_address": account_address,
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "ctx": {"expected": "'buy' or 'sell'"},
                    "input": "buyyyyy",
                    "loc": ["query", "order_type"],
                    "msg": "Input should be 'buy' or 'sell'",
                    "type": "enum",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_4
    # Method Not Allowed
    def test_error_4(self, client: TestClient, session: Session):
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address

        resp = client.post(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: POST, url: /DEX/Market/OrderBook/Coupon",
        }

    # Error_5_1
    # Coupon token is not enabled
    def test_error_5_1(self, client: TestClient, session: Session):
        exchange_address = to_checksum_address(
            "0x421b0ee9a0a3d1887bd4972790c50c092e1aec1b"
        )
        config.COUPON_TOKEN_ENABLED = False
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        agent_address = eth_account["agent"]["account_address"]

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/Market/OrderBook/Coupon",
        }

    # Error_5_2
    # Exchange address is not set
    def test_error_5_2(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        agent_address = eth_account["agent"]["account_address"]

        request_params = {
            "token_address": token_address,
            "exchange_agent_address": agent_address,
            "order_type": "sell",
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/Market/OrderBook/Coupon",
        }
