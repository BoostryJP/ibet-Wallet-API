"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from app.model import Position, Listing


class TestV2TokenHolders:
    """
    Test Case for v2.token.TokenHolders
    """

    # テスト対象API
    apiurl_base = '/v2/Token/{contract_address}/Holders'

    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"

    @staticmethod
    def insert_listing(session, listing: dict):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        session.add(_listing)

    @staticmethod
    def insert_position(session, position: dict):
        _position = Position()
        _position.token_address = position["token_address"]
        _position.account_address = position["account_address"]
        _position.balance = position["balance"]
        session.add(_position)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # Positionデータなし
    def test_normal_1(self, client, session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_2
    # Positionデータあり：1件
    def test_normal_2(self, client, session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        position = {
            "token_address": self.token_address,
            "account_address": "0x52D0784B3460E206ED69393ae1f9Ed37941089eD",
            "balance": 10
        }
        self.insert_position(session, position=position)

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = [
            {
                "token_address": self.token_address,
                "account_address": "0x52D0784B3460E206ED69393ae1f9Ed37941089eD",
                "amount": 10
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_3
    # Positionデータあり：2件
    def test_normal_3(self, client, session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        position = {
            "token_address": self.token_address,
            "account_address": "0x52D0784B3460E206ED69393ae1f9Ed37941089eD",
            "balance": 10
        }
        self.insert_position(session, position=position)

        # ２件目
        position = {
            "token_address": self.token_address,
            "account_address": "0x553c29335Aab4A0C1c10B86E46C6b0822E8753a3",
            "balance": 20
        }
        self.insert_position(session, position=position)

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = [
            {
                "token_address": self.token_address,
                "account_address": "0x52D0784B3460E206ED69393ae1f9Ed37941089eD",
                "amount": 10
            },
            {
                "token_address": self.token_address,
                "account_address": "0x553c29335Aab4A0C1c10B86E46C6b0822E8753a3",
                "amount": 20
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_4
    # Positionデータあり：1件（保有数量0）
    def test_normal_4(self, client, session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        position = {
            "token_address": self.token_address,
            "account_address": "0x52D0784B3460E206ED69393ae1f9Ed37941089eD",
            "balance": 0
        }
        self.insert_position(session, position=position)

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    ####################################################################
    # Error
    ####################################################################

    # Error_1
    # 無効なコントラクトアドレス
    # 400
    def test_error_1(self, client):
        apiurl = self.apiurl_base.format(contract_address='0xabcd')
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'invalid contract_address'
        }

    # Error_2
    # 取扱していないトークン
    # 404
    def test_error_2(self, client, session):
        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + self.token_address
        }
