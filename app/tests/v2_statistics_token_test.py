# -*- coding: utf-8 -*-
from app.model import Position


class TestV2StatisticsToken:
    """
    Test Case for v2.statistics.Token
    """

    # テスト対象API
    apiurl_base = '/v2/Statistics/Token/'  # {contract_address}

    @staticmethod
    def insert_position(session, token_address, account_address, balance):
        position = Position()
        position.token_address = token_address
        position.account_address = account_address
        position.balance = balance
        session.add(position)

    ####################################################################
    # Normal
    ####################################################################

    # Normal_1
    # Positionデータなし
    def test_normal_1(self, client, db):
        apiurl = self.apiurl_base + "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a"
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 0}  # 0件

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_2
    # Positionデータあり
    def test_normal_2(self, client, session):
        # データ準備 1
        self.insert_position(
            session,
            "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a",
            "0x342d0BfeD067eF22e2818E8f8731108a45F6Dd35",
            100
        )

        # データ準備 2
        self.insert_position(
            session,
            "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a",
            "0x8587F9Ba6E5910e693A5E6190C98F029689A1dA3",
            200
        )

        apiurl = self.apiurl_base + "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a"
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 2}  # 2件

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_3
    # Positionデータあり（残高0のデータが存在）
    def test_normal_3(self, client, session):
        # データ準備１
        self.insert_position(
            session,
            "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a",
            "0x342d0BfeD067eF22e2818E8f8731108a45F6Dd35",
            100
        )

        # データ準備２
        self.insert_position(
            session,
            "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a",
            "0x8587F9Ba6E5910e693A5E6190C98F029689A1dA3",
            0
        )

        apiurl = self.apiurl_base + "0x17688FfEA4366fD455DfE2C9e9090fa502A1540a"
        query_string = ""
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {'holders_count': 1}  # 1件

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
        apiurl = self.apiurl_base + '0xabcd'

        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'invalid contract_address'
        }
