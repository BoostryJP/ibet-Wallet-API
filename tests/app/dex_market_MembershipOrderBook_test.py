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
import sys

from eth_utils import to_checksum_address

from app import config
from app.model.db import (
    IDXOrder as Order,
    IDXAgreement as Agreement,
    AgreementStatus
)
from tests.account_config import eth_account


class TestDEXMarketMembershipOrderBook:

    # テスト対象API
    apiurl = '/DEX/Market/OrderBook/Membership'

    # 環境変数設定
    config.AGENT_ADDRESS = eth_account['agent']['account_address']

    # ＜正常系1-1-1＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> リスト1件が返却
    def test_membershiporderbook_normal_1_1_1(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
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
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系1-1-2＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> リスト1件が返却
    def test_membershiporderbook_normal_1_1_2(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy"
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
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
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系1-2＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と異なるトークンアドレス　※
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_1_2(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",
            "order_type": "buy",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系1-3＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 売り注文　※
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_1_3(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系1-4＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文と同一のアカウントアドレス　※
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_1_4(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系1-5＞
    # 未約定＆未キャンセルの売り注文が1件存在
    # 限界値
    def test_membershiporderbook_normal_1_5(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.id = sys.maxsize
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = sys.maxsize
        order.unique_order_id = exchange_address + '_' + str(sys.maxsize)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = sys.maxsize
        order.amount = sys.maxsize
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
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
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系1-6＞
    # 未約定＆未キャンセルの売り注文が1件存在（ただし、他のExchangeのデータ）
    # 以下の条件でリクエスト
    #   1) 売り注文と同一トークンアドレス
    #   2) 買い注文
    #   3) 売り注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_1_6(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43"
        order.order_id = 1
        order.unique_order_id = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43" + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2-1＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 売り注文
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> リスト1件が返却
    def test_membershiporderbook_normal_2_1(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
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
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2-2＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と異なるトークンアドレス　※
    #   2) 売り注文
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_2_2(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",
            "order_type": "sell",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2-3＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 買い注文　※
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_2_3(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2-4＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 売り注文
    #   3) 買い注文と同一のアカウントアドレス　※
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_2_4(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": account_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2-5＞
    # 未約定＆未キャンセルの買い注文が1件存在
    # 限界値
    def test_membershiporderbook_normal_2_5(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.id = sys.maxsize
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = sys.maxsize
        order.unique_order_id = exchange_address + '_' + str(sys.maxsize)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = sys.maxsize
        order.amount = sys.maxsize
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
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
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2-6＞
    # 未約定＆未キャンセルの買い注文が1件存在（ただし、他のExchangeのデータ）
    # 以下の条件でリクエスト
    #   1) 買い注文と同一トークンアドレス
    #   2) 売り注文
    #   3) 買い注文とは異なるアカウントアドレス
    #
    # -> ゼロ件リストが返却
    def test_membershiporderbook_normal_2_6(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43"
        order.order_id = 1
        order.unique_order_id = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43" + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3-1＞
    # 未約定＆未キャンセルの売り注文が複数件存在
    # -> リストのソート順が価格の昇順
    def test_membershiporderbook_normal_3_1(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(2)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = False
        order.price = 999
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{
            "exchange_address": exchange_address,
            'order_id': 2,
            'price': 999,
            'amount': 100,
            'account_address': account_address,
        }, {
            "exchange_address": exchange_address,
            'order_id': 1,
            'price': 1000,
            'amount': 100,
            'account_address': account_address,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3-2＞
    # 未約定＆未キャンセルの買い注文が複数件存在
    # -> リストのソート順が価格の降順
    def test_membershiporderbook_normal_3_2(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        agent_address = eth_account['agent']['account_address']

        # テストデータを挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 1
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_address
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(2)
        order.account_address = account_address
        order.counterpart_address = ''
        order.is_buy = True
        order.price = 1001
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        # リクエスト情報
        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": agent_address,
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{
            "exchange_address": exchange_address,
            'order_id': 2,
            'price': 1001,
            'amount': 100,
            'account_address': account_address,
        }, {
            "exchange_address": exchange_address,
            'order_id': 1,
            'price': 1000,
            'amount': 100,
            'account_address': account_address,
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4-1＞
    # 約定済み（※部分約定,約定否認含む）の売り注文が複数存在:アカウントアドレス指定
    #  -> 未約定のOrderBookリストが返却される
    def test_membershiporderbook_normal_4_1(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616"  # 注文者2
        ]
        agent_address = eth_account['agent']['account_address']

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + '_' + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        agreement.unique_order_id = exchange_address + '_' + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_addresses[0],
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{
            "exchange_address": exchange_address,
            "order_id": 2,
            "price": 3000,
            "amount": 50,
            "account_address": account_addresses[2],
        }, {
            "exchange_address": exchange_address,
            "order_id": 3,
            "price": 6000,
            "amount": 70,
            "account_address": account_addresses[1],
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4-2＞
    # 約定済み（※部分約定,約定否認含む）の買い注文が複数存在:アカウントアドレス指定
    #  -> 未約定のOrderBookリストが返却される
    def test_membershiporderbook_normal_4_2(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616"  # 注文者2
        ]
        agent_address = eth_account['agent']['account_address']

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + '_' + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        agreement.unique_order_id = exchange_address + '_' + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "account_address": account_addresses[0],
        }

        resp = client.simulate_post(self.apiurl, json=request_body)

        assumed_body = [
            {
                'exchange_address': exchange_address,
                'order_id': 3,
                'price': 6000,
                'amount': 70,
                'account_address': account_addresses[1]
            }, {
                'exchange_address': exchange_address,
                'order_id': 2,
                'price': 3000,
                'amount': 50,
                'account_address': account_addresses[2]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4-3＞
    # 約定済み（※部分約定,約定否認含む）の売り注文が複数存在:アカウントアドレス指定なし
    #  -> 未約定のOrderBookリストが返却される
    def test_membershiporderbook_normal_4_3(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616"  # 注文者2
        ]
        agent_address = eth_account['agent']['account_address']

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + '_' + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        agreement.unique_order_id = exchange_address + '_' + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_body = {
            "token_address": token_address,
            "order_type": "buy",
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{
            "exchange_address": exchange_address,
            "order_id": 0,
            "price": 1000,
            "amount": 100,
            "account_address": account_addresses[0],
        }, {
            "exchange_address": exchange_address,
            "order_id": 2,
            "price": 3000,
            "amount": 50,
            "account_address": account_addresses[2],
        }, {
            "exchange_address": exchange_address,
            "order_id": 3,
            "price": 6000,
            "amount": 70,
            "account_address": account_addresses[1],
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4-4＞
    # 約定済み（※部分約定,約定否認含む）の買い注文が複数存在:アカウントアドレス指定なし
    #  -> 未約定のOrderBookリストが返却される
    def test_membershiporderbook_normal_4_4(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616"  # 注文者2
        ]
        agent_address = eth_account['agent']['account_address']

        # Orderの情報を挿入
        order = Order()
        order.token_address = token_address
        order.exchange_address = exchange_address
        order.order_id = 0
        order.unique_order_id = exchange_address + '_' + str(0)
        order.account_address = account_addresses[0]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(1)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(2)
        order.account_address = account_addresses[2]
        order.counterpart_address = ''
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
        order.unique_order_id = exchange_address + '_' + str(3)
        order.account_address = account_addresses[1]
        order.counterpart_address = ''
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
        agreement.unique_order_id = exchange_address + '_' + str(1)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(2)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 0
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 10
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 1
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 20
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 3
        agreement.agreement_id = 2
        agreement.exchange_address = exchange_address
        agreement.unique_order_id = exchange_address + '_' + str(3)
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 70
        agreement.status = AgreementStatus.CANCELED.value
        session.add(agreement)

        request_body = {
            "token_address": token_address,
            "order_type": "sell",
        }

        resp = client.simulate_post(self.apiurl, json=request_body)

        assumed_body = [
            {
                'exchange_address': exchange_address,
                'order_id': 3,
                'price': 6000,
                'amount': 70,
                'account_address': account_addresses[1]
            },
            {
                'exchange_address': exchange_address,
                'order_id': 2,
                'price': 3000,
                'amount': 50,
                'account_address': account_addresses[2]
            }, {
                'exchange_address': exchange_address,
                'order_id': 0,
                'price': 1000,
                'amount': 100,
                'account_address': account_addresses[0]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_membershiporderbook_error_1(self, client, session):
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_address': ['required field'],
                'order_type': ['required field'],
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_membershiporderbook_error_2(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-1：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_membershiporderbook_error_3_1(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレスが短い
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_address,
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-2：入力値エラー（token_addressがstring以外）
    def test_membershiporderbook_error_3_2(self, client, session):
        token_address = 123456789123456789123456789123456789
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_address,
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_address': ['must be of string type']
            }
        }

    # エラー系4-1：入力値エラー（account_addressがアドレスフォーマットではない）
    def test_membershiporderbook_error_4_1(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_address,
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4-2：入力値エラー（account_addressがstring以外）
    def test_membershiporderbook_error_4_2(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = 123456789123456789123456789123456789

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "account_address": account_address,
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address': ['must be of string type']
            }
        }

    # エラー系5：入力値エラー（order_typeがbuy/sell以外）
    def test_membershiporderbook_error_5(self, client, session):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buyyyyy",
            "account_address": account_address,
        }

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_type': ['unallowed value buyyyyy']
            }
        }

    # エラー系6：HTTPメソッドが不正
    def test_membershiporderbook_error_6(self, client, session):
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address

        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /DEX/Market/OrderBook/Membership'
        }

    # エラー系7：取扱トークン対象外
    def test_membershiporderbook_error_7(self, client, session):
        exchange_address = \
            to_checksum_address("0xe88d2561d2ffbb98a6a1982f7324f69df7f444c6")
        config.MEMBERSHIP_TOKEN_ENABLED = False
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange_address

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /DEX/Market/OrderBook/Membership'
        }

    # エラー系8：exchangeアドレス未設定
    def test_membershiporderbook_error_8(self, client, session):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None

        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /DEX/Market/OrderBook/Membership'
        }
