import json

from falcon.util import json as util_json

class TestV1LatestVersion():
    # テスト対象API
    apiurl = "/v1/LatestVersion"
    request_body = json.dumps({})
    
    # ＜正常系1＞
    # iOSの場合
    def test_latest_version_1(self, client):
        query_string = "platform=ios"

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            "required_version":"2.0.0",
            "type":"force",
            "update_url":"https://itunes.apple.com/jp/app/mdaq/id489127768?mt=8"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # Androidの場合
    def test_latest_version_2(self, client):
        query_string = "platform=android"

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            "required_version":"2.0.0",
            "type":"force",
            "update_url":"https://play.google.com/store/apps/details?id=jp.co.nomura.nomurastock"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    #＜異常系1＞
    # iOS, Android以外の場合
    def test_latest_version_error1(self, client):
        query_string = "platform=XXX"

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            "required_version":"2.0.0",
            "type":"force",
            "update_url":"https://itunes.apple.com/jp/app/mdaq/id489127768?mt=8"
        }

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'platform':'unallowed value XXX'
            }
        }

