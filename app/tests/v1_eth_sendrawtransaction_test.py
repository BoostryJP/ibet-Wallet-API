# -*- coding: utf-8 -*-
import pytest
import json
import os

from web3 import Web3

from app import config
from .account_config import eth_account


# sendRawTransaction API
# /v1/Eth/SendRawTransaction
class TestV1EthSendRawTransaction():

    # テスト対象API
    apiurl = '/v1/Eth/SendRawTransaction/'

    # ＜正常系1＞
    # 入力リストが空
    def test_sendraw_normal_1(self, client):
        request_params = {"raw_tx_hex_list": []}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー（Not Supported）
    def test_sendraw_error_1(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/Eth/SendRawTransaction'
        }

    # ＜エラー系2＞
    # headersなし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_2(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3＞
    # 入力値なし
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_3(self, client):
        request_params = {}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'required field'
            }
        }

    # ＜エラー系4＞
    # 入力値が正しくない（リストではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_4(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": raw_tx_1}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': 'must be of list type'
            }
        }

    # ＜エラー系5＞
    # 入力値が正しくない（String型ではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_5(self, client):
        raw_tx_1 = 1234
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'raw_tx_hex_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # ＜エラー系6＞
    # 入力値が正しくない（rawtransactionではない）
    # -> 400エラー（InvalidParameterError）
    def test_sendraw_error_6(self, client):
        raw_tx_1 = "some_raw_tx_1"
        request_params = {"raw_tx_hex_list": [raw_tx_1]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code':
            88,
            'message':
            'Invalid Parameter',
            'description':
            "when sending a str, it must be a hex string. Got: 'some_raw_tx_1'"
        }
