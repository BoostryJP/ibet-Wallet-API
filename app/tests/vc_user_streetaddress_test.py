# -*- coding: utf-8 -*-
import json
import os


# 住所検索API
# /v1/User/StreetAddress/{postal_code}
class TestV1StreetAddress:

    # テスト対象API
    apiurl = '/v1/User/StreetAddress'

    # ＜正常系1＞
    # 通常参照（登録済）
    def test_streetaddress_normal_1(self, client):
        postal_code = '1670052'

        resp = client.simulate_get(self.apiurl + '/' + postal_code)

        assumed_body = [{"jis_code":"13115","zip_code":"1670052","prefecture_name_kana":"ﾄｳｷｮｳﾄ","city_name_kana":"ｽｷﾞﾅﾐｸ","town_name_kana":"ﾐﾅﾐｵｷﾞｸﾎﾞ","prefecture_name":"東京都","city_name":"杉並区","town_name":"南荻窪"}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # 7桁の数字ではない
    # -> 400エラー
    def test_streetaddress_error_1(self, client):
        postal_code = 'aaa'

        resp = client.simulate_get(self.apiurl + '/' + postal_code)


        assert resp.status_code == 400
        assert resp.json['meta'] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "postal_code: aaa"
            }

    # ＜エラー系2＞
    # 7桁の数字だがファイルが存在しない
    def test_ptreetaddress_error_2(self, client):
        postal_code = '9999999'

        resp = client.simulate_get(self.apiurl + '/' + postal_code)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            "code": 30,
            "message": "Data Not Exists",
            "description": "postal_code: 9999999"
            }