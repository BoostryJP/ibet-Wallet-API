# -*- coding: utf-8 -*-

import app.model
from app.model import Order, Agreement, AgreementStatus


class TestV1OrderBook():
    # テスト対象API
    apiurl_base = '/v1/OrderBook'

    # 正常系1-1: 板情報が存在(未約定)
    def test_normal_1_1(self, client, session):
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
        resp = client.simulate_post(self.apiurl_base, json=request_body)
        assumed_body = [{"order_id": 1, "price": 1000, "amount": 100}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系1-2: 板情報が存在(約定済み、部分約定含む)
    def test_normal_1_2(self, client, session):
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

        resp = client.simulate_post(self.apiurl_base, json=request_body)
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
