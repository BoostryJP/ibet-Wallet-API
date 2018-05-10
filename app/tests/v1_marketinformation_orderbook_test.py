# -*- coding: utf-8 -*-
import json

import app.model
from app.model import Order, Agreement, AgreementStatus


class TestV1OrderBook():

    # テスト対象API
    apiurl = '/v1/OrderBook'

    # 正常系1: 板情報が存在(未約定, buy)
    def test_orderbook_normal_1(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"

        order = Order()
        order.id = 1
        order.token_address = token_address
        order.account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43"
        order.is_cancelled = False
        session.add(order)

        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 10000,
            "amount": 1000,
            "account_address": "0xeb6e99675595fb052cc68da0eeecb2d5a3826378",
        }
        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{"order_id": 1, "price": 1000, "amount": 100}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2: 板情報が存在(未約定, sell)
    def test_orderbook_normal_2(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"

        order = Order()
        order.id = 1
        order.token_address = token_address
        order.account_address = "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A"
        order.is_buy = True
        order.price = 1000
        order.amount = 100
        order.agent_address = "0xE6E8eb2F31Fd906F2681EB0a65610bfe92cf6c43"
        order.is_cancelled = False
        session.add(order)

        request_body = {
            "token_address": token_address,
            "order_type": "sell",
            "price": 10000,
            "amount": 1000,
            "account_address": "0xeb6e99675595fb052cc68da0eeecb2d5a3826378",
        }
        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{"order_id": 1, "price": 1000, "amount": 100}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3: 板情報が存在(約定済み、部分約定含む)
    def test_orderbook_normal_3(self, client, session):
        token_address = "0x4814B3b0b7aC56097F280B254F8A909A76ca7f51"
        account_addresses = [
            "0x26E9F441d9bE19E42A5a0A792E3Ef8b661182c9A",  # client
            "0x31b98d14007bdee637298086988a0bbd31184523",  # 注文者1
            "0x52c3a9b0f293cac8c1baabe5b62524a71211a616"  # 注文者2
        ]
        agent_address = "0x4cc120790781c9b61bb8d9893d439efdf02e2d30"

        order = Order()
        order.id = 0
        order.token_address = token_address
        order.account_address = account_addresses[1]
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.id = 1
        order.token_address = token_address
        order.account_address = account_addresses[1]
        order.is_buy = False
        order.price = 2000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.id = 2
        order.token_address = token_address
        order.account_address = account_addresses[2]
        order.is_buy = False
        order.price = 3000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        order = Order()
        order.id = 3
        order.token_address = token_address
        order.account_address = account_addresses[2]
        order.is_buy = False
        order.price = 6000
        order.amount = 100
        order.agent_address = agent_address
        order.is_cancelled = False
        session.add(order)

        agreement = Agreement()
        agreement.order_id = 1
        agreement.agreement_id = 0
        agreement.counterpart_address = account_addresses[2]
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        agreement = Agreement()
        agreement.order_id = 2
        agreement.agreement_id = 0
        agreement.counterpart_address = account_addresses[1]
        agreement.amount = 50
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        request_body = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": 200,
            "account_address": "0xeb6e99675595fb052cc68da0eeecb2d5a3826378",
        }

        resp = client.simulate_post(self.apiurl, json=request_body)
        assumed_body = [{
            "order_id": 0,
            "price": 1000,
            "amount": 100
        }, {
            "order_id": 2,
            "price": 3000,
            "amount": 50
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_orderbook_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'token_address': 'required field',
                'amount': 'required field',
                'order_type': 'required field',
                'price': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_orderbook_error_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-1：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_orderbook_error_3_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74" #アドレスが短い
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3-2：入力値エラー（token_addressがstring以外）
    def test_orderbook_error_3_2(self, client):
        token_address = 123456789123456789123456789123456789
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4-1：入力値エラー（account_addressがアドレスフォーマットではない）
    def test_orderbook_error_4_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637" #アドレスが短い

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4-2：入力値エラー（account_addressがstring以外）
    def test_orderbook_error_4_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        account_address = 123456789123456789123456789123456789

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系5：入力値エラー（order_typeがbuy/sell以外）
    def test_orderbook_error_5(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buyyyyy",
            "price": 5000,
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系6：入力値エラー（priceが数字以外）
    def test_orderbook_error_6(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": "5000",
            "amount": 200,
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系7：入力値エラー（amountが数字以外）
    def test_orderbook_error_7(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a3826378"

        request_params = {
            "token_address": token_address,
            "order_type": "buy",
            "price": 5000,
            "amount": "200",
            "account_address": account_address,
        }

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系8：HTTPメソッドが不正
    def test_orderbook_error_8(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/OrderBook'
        }
