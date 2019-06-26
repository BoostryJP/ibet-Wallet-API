# -*- coding: utf-8 -*-
import json
import os
from app import config


# 手数料返却API
# /v1/Stripe/Constants
class TestV1Constants:

    # テスト対象API
    apiurl = '/v1/Stripe/Constants'

    # ＜正常系1＞
    # 通常参照（登録済）
    def test_stripe_feeinfo_normal_1(self, client):
        assumed_body = {
                    'commitment_fee': float(config.STRIPE_FEE),
                    'fix_fee': 0,
                    'minimum_value': int(config.STRIPE_MINIMUM_VALUE), 
                    'maximum_value': int(config.STRIPE_MAXIMUM_VALUE)
                }

        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body