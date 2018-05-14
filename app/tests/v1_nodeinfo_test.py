# -*- coding: utf-8 -*-
import json
import os

from web3 import Web3

from app import config


# ノード情報取得API
# /v1/NodeInfo
class TestV1NodeInfo():

    # テスト対象API
    apiurl = '/v1/NodeInfo/'

    # ＜正常系1＞
    # 通常参照
    def test_nodeinfo_normal_1(self, client):
        resp = client.simulate_get(self.apiurl)

        whitelist_address = os.environ.get('WHITE_LIST_CONTRACT_ADDRESS')
        whitelist_abi = config.WHITE_LIST_CONTRACT_ABI

        personalinfo_address = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')
        personalinfo_abi = config.PERSONAL_INFO_CONTRACT_ABI

        exchange_address = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        exchange_abi = config.IBET_EXCHANGE_CONTRACT_ABI

        assumed_body = {
            'white_list_address': whitelist_address,
            'white_list_abi': whitelist_abi,
            'personal_info_address': personalinfo_address,
            'personal_info_abi': personalinfo_abi,
            'ibet_exchange_address': exchange_address,
            'ibet_exchange_abi': exchange_abi
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_nodeinfo_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v1/NodeInfo'
        }
