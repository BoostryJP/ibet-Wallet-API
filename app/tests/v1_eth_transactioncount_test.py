# -*- coding: utf-8 -*-
import pytest
import json
import os

from web3 import Web3

from app import config
from .account_config import eth_account


# nonce取得API
# /v1/Eth/TransactionCount/{eth_address}
class TestV1EthTransactionCount():

    # テスト対象API
    apiurl_base = '/v1/Eth/TransactionCount/'

    # ＜正常系1＞
    # トランザクション未実行のアドレス
    # -> nonce = 0
    def test_transactioncount_normal_1(self, client):
        # 任意のアドレス
        some_account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"

        apiurl = self.apiurl_base + some_account_address
        resp = client.simulate_get(apiurl)

        assumed_body = {'chainid': '2017', 'gasprice': 0, 'nonce': 0}

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # トランザクション実行済みのアドレス
    # -> nonce = （ブロックを直接参照した情報と一致）
    def test_transactioncount_normal_2(self, client, shared_contract):
        # deployerのアドレス
        eth_address = eth_account['deployer']['account_address']

        apiurl = self.apiurl_base + eth_address
        resp = client.simulate_get(apiurl)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        nonce = web3.eth.getTransactionCount(eth_address)

        assumed_body = {'chainid': '2017', 'gasprice': 0, 'nonce': nonce}

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_transactioncount_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl_base, headers=headers, body=request_body)

        assert resp.status_code == 404

    # ＜エラー系2＞
    # addressのフォーマットが正しくない
    # -> 400エラー（InvalidParameterError）
    def test_transactioncount_error_2(self, client):
        some_account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9" # アドレス長が短い

        apiurl = self.apiurl_base + some_account_address
        resp = client.simulate_get(apiurl)

        assert resp.status_code == 400
        assert resp.json['meta'] == {'code': 88, 'message': 'Invalid Parameter'}

    # ＜エラー系3＞
    # addressが未設定
    # -> 400エラー
    def test_transactioncount_error_3(self, client):
        apiurl = self.apiurl_base
        resp = client.simulate_get(apiurl)

        assert resp.status_code == 404
