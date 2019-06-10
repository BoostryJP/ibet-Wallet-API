import os
from app import config


class TestV1RequiredVersion:
    # テスト対象API
    apiurl = "/v1/RequiredVersion"

    @staticmethod
    def set_env():
        config.TMRAPP_REQUIRED_VERSION_IOS = '1.0.0'
        config.TMRAPP_FORCE_UPDATE_IOS = 'True'
        config.TMRAPP_UPDATE_URL_SCHEME_IOS = 'itms-apps://itunes.apple.com/jp/app/mdaq/id489127768?mt=8'
        config.TMRAPP_UPDATE_URL_IOS = 'https://itunes.apple.com/jp/app/mdaq/id489127768?mt=8'
        config.TMRAPP_REQUIRED_VERSION_ANDROID = '1.0.0'
        config.TMRAPP_FORCE_UPDATE_ANDROID = 'True'
        config.TMRAPP_UPDATE_URL_SCHEME_ANDROID = 'market://details?id=jp.co.nomura.nomurastock'
        config.TMRAPP_UPDATE_URL_ANDROID = 'https://play.google.com/store/apps/details?id=jp.co.nomura.nomurastock'
        return

    # ＜正常系1＞
    # iOSの場合
    def test_required_version_1(self, client):
        TestV1RequiredVersion.set_env()
        query_string = "platform=ios"

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            "required_version": "1.0.0",
            "force": True,
            "update_url_scheme": "itms-apps://itunes.apple.com/jp/app/mdaq/id489127768?mt=8",
            "update_url": "https://itunes.apple.com/jp/app/mdaq/id489127768?mt=8"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # Androidの場合
    def test_required_version_2(self, client):
        TestV1RequiredVersion.set_env()
        query_string = "platform=android"

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            "required_version": "1.0.0",
            "force": True,
            "update_url_scheme": "market://details?id=jp.co.nomura.nomurastock",
            "update_url": "https://play.google.com/store/apps/details?id=jp.co.nomura.nomurastock"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜異常系1＞
    # iOS, Android以外の場合
    def test_required_version_error_1(self, client):
        TestV1RequiredVersion.set_env()
        query_string = "platform=XXX"

        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'platform': 'unallowed value XXX'
            }
        }
