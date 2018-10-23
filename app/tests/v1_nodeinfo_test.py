# -*- coding: utf-8 -*-
import json
import os

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

        contracts = json.load(open('data/contracts.json' , 'r'))

        whitelist_address = os.environ.get('WHITE_LIST_CONTRACT_ADDRESS')
        whitelist_abi = contracts['WhiteList']['abi']

        personalinfo_address = os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS')
        personalinfo_abi = contracts['PersonalInfo']['abi']

        bond_exchange_address = \
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        bond_exchange_abi = contracts['IbetStraightBondExchange']['abi']

        membership_exchange_address = \
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
        membership_exchange_abi = contracts['IbetMembershipExchange']['abi']

        coupon_exchange_address = \
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS')
        coupon_exchange_abi = contracts['IbetCouponExchange']['abi']

        agent_address = os.environ.get('AGENT_ADDRESS')

        assumed_body = {
            'white_list_address': whitelist_address,
            'white_list_abi': whitelist_abi,
            'personal_info_address': personalinfo_address,
            'personal_info_abi': personalinfo_abi,
            'ibet_exchange_address': bond_exchange_address,
            'ibet_exchange_abi': bond_exchange_abi,
            'ibet_membership_exchange_address': membership_exchange_address,
            'ibet_membership_exchange_abi': membership_exchange_abi,
            'ibet_coupon_exchange_address': coupon_exchange_address,
            'ibet_coupon_exchange_abi': coupon_exchange_abi,
            'agent_address': agent_address
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
