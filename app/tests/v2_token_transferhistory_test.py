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

from app.model import Listing, Transfer


class TestV2TransferHistory:
    """
    Test Case for v2.token.TransferHistory
    """

    # テスト対象API
    apiurl_base = "/v2/Token/{contract_address}/TransferHistory"

    transaction_hash = "0xc99116e27f0c40201a9e907ad5334f4477863269b90a94444d11a1bc9b9315e6"
    token_address = "0xe883A6f441Ad5682d37DF31d34fc012bcB07A740"
    from_address = "0xF13D2aCe101F1e4B55d96d66fBF18aD8a8aF22bF"
    to_address = "0x6431d02363FC69fFD9F69CAa4E05E96d4e79f3da"

    @staticmethod
    def insert_listing(session, listing: dict):
        _listing = Listing()
        _listing.token_address = listing["token_address"]
        _listing.is_public = listing["is_public"]
        session.add(_listing)

    @staticmethod
    def insert_transfer_event(session, transfer_event: dict):
        _transfer = Transfer()
        _transfer.transaction_hash = transfer_event["transaction_hash"]
        _transfer.token_address = transfer_event["token_address"]
        _transfer.from_address = transfer_event["from_address"]
        _transfer.to_address = transfer_event["to_address"]
        _transfer.value = transfer_event["value"]
        session.add(_transfer)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # Transferイベントなし
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
    # Transferイベントあり：1件
    def test_normal_2(self, client, session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        transfer_event = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10
        }
        self.insert_transfer_event(session, transfer_event=transfer_event)

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for item in resp.json["data"]:
            assert item["transaction_hash"] == transfer_event["transaction_hash"]
            assert item["token_address"] == transfer_event["token_address"]
            assert item["from_address"] == transfer_event["from_address"]
            assert item["to_address"] == transfer_event["to_address"]
            assert item["value"] == transfer_event["value"]

    # Normal_3
    # Transferイベントあり：2件
    def test_normal_3(self, client, session):
        listing = {
            "token_address": self.token_address,
            "is_public": True,
        }
        self.insert_listing(session, listing=listing)

        # １件目
        transfer_event_1 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": 10
        }
        self.insert_transfer_event(session, transfer_event=transfer_event_1)

        # ２件目
        transfer_event_2 = {
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.to_address,
            "to_address": self.from_address,
            "value": 20
        }
        self.insert_transfer_event(session, transfer_event=transfer_event_2)

        apiurl = self.apiurl_base.format(contract_address=self.token_address)
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        assert resp.json["data"][0]["transaction_hash"] == transfer_event_1["transaction_hash"]
        assert resp.json["data"][0]["token_address"] == transfer_event_1["token_address"]
        assert resp.json["data"][0]["from_address"] == transfer_event_1["from_address"]
        assert resp.json["data"][0]["to_address"] == transfer_event_1["to_address"]
        assert resp.json["data"][0]["value"] == transfer_event_1["value"]

        assert resp.json["data"][1]["transaction_hash"] == transfer_event_2["transaction_hash"]
        assert resp.json["data"][1]["token_address"] == transfer_event_2["token_address"]
        assert resp.json["data"][1]["from_address"] == transfer_event_2["from_address"]
        assert resp.json["data"][1]["to_address"] == transfer_event_2["to_address"]
        assert resp.json["data"][1]["value"] == transfer_event_2["value"]

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
