# -*- coding: utf-8 -*-
import json

from app import config


class TestNodeInfo:
    # テスト対象API
    apiurl = '/v2/NodeInfo/'

    # ＜正常系1＞
    # 通常参照
    def test_nodeinfo_normal_1(self, client):
        resp = client.simulate_get(self.apiurl)

        payment_gateway = json.load(open("app/contracts/json/PaymentGateway.json", "r"))
        personal_info = json.load(open("app/contracts/json/PersonalInfo.json", "r"))
        ibet_straightbond_exchange = json.load(open("app/contracts/json/IbetStraightBondExchange.json", "r"))
        ibet_membership_exchange = json.load(open("app/contracts/json/IbetMembershipExchange.json", "r"))
        ibet_coupon_exchange = json.load(open("app/contracts/json/IbetCouponExchange.json", "r"))
        ibet_otc_exchange = json.load(open("app/contracts/json/IbetOTCExchange.json", "r"))

        payment_gateway_address = config.PAYMENT_GATEWAY_CONTRACT_ADDRESS
        payment_gateway_abi = payment_gateway['abi']

        personalinfo_address = config.PERSONAL_INFO_CONTRACT_ADDRESS
        personalinfo_abi = personal_info['abi']

        bond_exchange_address = config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        bond_exchange_abi = ibet_straightbond_exchange['abi']

        membership_exchange_address = config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
        membership_exchange_abi = ibet_membership_exchange['abi']

        coupon_exchange_address = config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
        coupon_exchange_abi = ibet_coupon_exchange['abi']

        otc_exchange_address = config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
        otc_exchange_abi = ibet_otc_exchange['abi']

        agent_address = config.AGENT_ADDRESS

        assumed_body = {
            'payment_gateway_address': payment_gateway_address,
            'payment_gateway_abi': payment_gateway_abi,
            'personal_info_address': personalinfo_address,
            'personal_info_abi': personalinfo_abi,
            'ibet_straightbond_exchange_address': bond_exchange_address,
            'ibet_straightbond_exchange_abi': bond_exchange_abi,
            'ibet_membership_exchange_address': membership_exchange_address,
            'ibet_membership_exchange_abi': membership_exchange_abi,
            'ibet_coupon_exchange_address': coupon_exchange_address,
            'ibet_coupon_exchange_abi': coupon_exchange_abi,
            'ibet_otc_exchange_address': otc_exchange_address,
            'ibet_otc_exchange_abi': otc_exchange_abi,
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
            'description': 'method: POST, url: /v2/NodeInfo'
        }
