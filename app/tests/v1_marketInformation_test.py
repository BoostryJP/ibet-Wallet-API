# -*- coding: utf-8 -*-

import app.model
from app.model import Order, Agreement, AgreementStatus

class TestV1OrderBook():
    # テスト対象API
    apiurl_base = '/v1/OrderBook'

    # 正常系1-1: 板情報が存在
    def test_normal_1_1(self, client, session):
        agreement = Agreement()
        agreement.order_id = 1
        agreement.agreement_id = 1
        agreement.counterpart_address = "0x1234"
        agreement.amount = 1234
        agreement.status = 1
        session.add(agreement)
        
        request_body = {
            "token_address": "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51",
            "order_type": "buy",
            "price": 10000,
            "amount": 100,
            "account_address": "0xeb6e99675595fb052cc68da0eeecb2d5a3826378",
        }
        resp = client.simulate_post(self.apiurl_base, json=request_body)
        assumed_body = [
	    {
                "order_id": 1,
		"price": 12000,
		"amount": 9999990
            }
	]
#        assert resp.status_code == 200
#        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
#        assert resp.json['data'] == assumed_body
