# -*- coding: utf-8 -*-
import json
import os

from .account_config import eth_account
from app import config
from app.model import Order, Agreement
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_payment_gateway, take_buy_bond_token, get_latest_orderid, \
    membership_issue, membership_offer, membership_get_latest_orderid, \
    membership_take_buy, issue_coupon_token, coupon_offer, \
    coupon_get_latest_orderid, coupon_take_buy


# [普通社債]歩み値参照API
# /v1/StraightBond/Tick/
class TestV1StraightBondTick():
    # テスト対象API
    apiurl = '/v1/StraightBond/Tick/'

    @staticmethod
    def generate_agree_event(bond_exchange, personal_info, payment_gateway):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': bond_exchange['address'],
            'faceValue': 10000,
            'interestRate': 1000,
            'interestPaymentDate1': '0101',
            'interestPaymentDate2': '0201',
            'interestPaymentDate3': '0301',
            'interestPaymentDate4': '0401',
            'interestPaymentDate5': '0501',
            'interestPaymentDate6': '0601',
            'interestPaymentDate7': '0701',
            'interestPaymentDate8': '0801',
            'interestPaymentDate9': '0901',
            'interestPaymentDate10': '1001',
            'interestPaymentDate11': '1101',
            'interestPaymentDate12': '1201',
            'redemptionDate': '20191231',
            'redemptionAmount': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # 発行体オペレーション
        bond_token = issue_bond_token(issuer, attribute)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        # 投資家オペレーション
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        latest_orderid = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, latest_orderid, 100)

        return bond_token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> ゼロ件リストが返却される
    def test_tick_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定（Agree）イベントがゼロ件の場合
    #  -> ゼロ件リストが返却される
    def test_tick_normal_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：約定イベントが有件の場合
    #  -> 約定イベントの情報が返却される
    def test_tick_normal_3(self, client, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']

        bond_token = TestV1StraightBondTick. \
            generate_agree_event(bond_exchange, personal_info, payment_gateway)

        token_address = bond_token['address']
        request_params = {"address_list": [token_address]}

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'][0]['token_address'] == token_address
        assert resp.json['data'][0]['tick'][0]['buy_address'] == eth_account['trader']['account_address']
        assert resp.json['data'][0]['tick'][0]['sell_address'] == eth_account['issuer']['account_address']
        assert resp.json['data'][0]['tick'][0]['price'] == 1000
        assert resp.json['data'][0]['tick'][0]['amount'] == 100

    # エラー系1：入力値エラー（request-bodyなし）
    def test_tick_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'address_list': 'required field'}
        }

    # エラー系2：入力値エラー（headersなし）
    def test_tick_error_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_tick_error_3(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_tick_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/StraightBond/Tick'
        }


# [会員権]歩み値参照API
# /v1/Membership/Tick/
class TestV1MembershipTick():
    # テスト対象API
    apiurl = '/v1/Membership/Tick/'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # 発行体オペレーション
        token = membership_issue(issuer, attribute)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        latest_orderid = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, latest_orderid, 100)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> ゼロ件リストが返却される
    def test_membership_tick_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定（Agree）イベントがゼロ件の場合
    #  -> ゼロ件リストが返却される
    def test_membership_tick_normal_2(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：約定イベントが有件の場合
    #  -> 約定イベントの情報が返却される
    def test_membership_tick_normal_3(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token = TestV1MembershipTick.generate_agree_event(exchange)
        token_address = token['address']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        request_params = {"address_list": [token_address]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'][0]['token_address'] == token_address
        assert resp.json['data'][0]['tick'][0]['buy_address'] == eth_account['trader']['account_address']
        assert resp.json['data'][0]['tick'][0]['sell_address'] == eth_account['issuer']['account_address']
        assert resp.json['data'][0]['tick'][0]['price'] == 1000
        assert resp.json['data'][0]['tick'][0]['amount'] == 100

    # エラー系1：入力値エラー（request-bodyなし）
    def test_membership_tick_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'address_list': 'required field'}
        }

    # エラー系2：入力値エラー（headersなし）
    def test_membership_tick_error_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_membership_tick_error_3(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_membership_tick_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/Membership/Tick'
        }


# [クーポン]歩み値参照API
# /v1/Coupon/Tick/
class TestV1CouponTick():
    # テスト対象API
    apiurl = '/v1/Coupon/Tick/'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': exchange['address'],
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }

        # 発行体オペレーション
        token = issue_coupon_token(issuer, attribute)
        coupon_offer(issuer, exchange, token, 10000, 1000)

        # 投資家オペレーション
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, latest_orderid, 100)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> ゼロ件リストが返却される
    def test_coupon_tick_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定（Agree）イベントがゼロ件の場合
    #  -> ゼロ件リストが返却される
    def test_coupon_tick_normal_2(self, client, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：約定イベントが有件の場合
    #  -> 約定イベントの情報が返却される
    def test_coupon_tick_normal_3(self, client, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token = TestV1CouponTick.generate_agree_event(exchange)
        token_address = token['address']
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        request_params = {"address_list": [token_address]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'][0]['token_address'] == token_address
        assert resp.json['data'][0]['tick'][0]['buy_address'] == eth_account['trader']['account_address']
        assert resp.json['data'][0]['tick'][0]['sell_address'] == eth_account['issuer']['account_address']
        assert resp.json['data'][0]['tick'][0]['price'] == 1000
        assert resp.json['data'][0]['tick'][0]['amount'] == 100

    # エラー系1：入力値エラー（request-bodyなし）
    def test_coupon_tick_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'address_list': 'required field'}
        }

    # エラー系2：入力値エラー（headersなし）
    def test_coupon_tick_error_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_coupon_tick_error_3(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_coupon_tick_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/Coupon/Tick'
        }


# [JDR]歩み値参照API
# /v1/JDR/Tick/
class TestV1JDRTick():
    # テスト対象API
    apiurl = '/v1/JDR/Tick'

    private_key = "0000000000000000000000000000000000000000000000000000000000000001"

    def _insert_test_data(self, session):
        self.session = session
        o = Order()
        o.token_address = '0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a'
        o.order_id = 1
        o.price = 70
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

        o = Order()
        o.token_address = '0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a'
        o.order_id = 2
        o.price = 80
        o.amount = 5
        o.is_buy = True
        o.is_cancelled = False
        session.add(o)

        a = Agreement()
        a.order_id = 1
        a.agreement_id = 101
        a.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.status = 1
        a.settlement_timestamp = '2019-11-13 16:23:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

        a = Agreement()
        a.order_id = 2
        a.agreement_id = 102
        a.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.status = 1
        a.settlement_timestamp = '2019-11-13 16:24:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> ゼロ件リストが返却される
    def test_jdr_tick_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_JDR_SWAP_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{'token_address': token_address, 'tick': []}]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：
    # 注文履歴がないtoken_addressの歩み値を取得しようとする
    # 入力されたtoken_addressが、DBの注文レコードに存在しない
    def test_jdr_tick_normal_2(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "address_list": ["0x0000000000000000000000000000000000000000"]
            },
            private_key=TestV1JDRTick.private_key)

        assumed_body = [{
            "tick": [],
            "token_address": "0x0000000000000000000000000000000000000000"
        }]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # 正常系3：
    # DBに約定情報レコードと注文レコードが存在し、歩み値を正常に取得
    def test_jdr_tick_normal_3(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "address_list": ["0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"]
            },
            private_key=TestV1JDRTick.private_key)

        assumed_body = [{
            "tick": [
                {
                    "block_timestamp": "2019/11/13 16:23:14",
                    "buy_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                    "sell_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                    "order_id": 1,
                    "agreement_id": 101,
                    "price": 70,
                    "amount": 5,
                    "isBuy": False
                },
                {
                    "block_timestamp": "2019/11/13 16:24:14",
                    "buy_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                    "sell_address": "0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb",
                    "order_id": 2,
                    "agreement_id": 102,
                    "price": 80,
                    "amount": 5,
                    "isBuy": False
                },
            ],
            "token_address": "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1a"
        }]

        assert resp.status_code == 200
        assert resp.json["data"] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_jdr_tick_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'address_list': 'required field'}
        }

    # エラー系2：入力値エラー（headersなし）
    def test_jdr_tick_error_2(self, client):
        token_address = "0xa4CEe3b909751204AA151860ebBE8E7A851c2A1b"
        request_params = {"address_list": [token_address]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系3：入力値エラー（token_addressがアドレスフォーマットではない）
    def test_jdr_tick_error_3(self, client, session):
        self._insert_test_data(session)

        resp = client.simulate_auth_post(
            self.apiurl,
            json={
                "address_list": ["0x"]
            },
            private_key=TestV1JDRTick.private_key)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # エラー系4：HTTPメソッドが不正
    def test_jdr_tick_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/JDR/Tick'
        }
