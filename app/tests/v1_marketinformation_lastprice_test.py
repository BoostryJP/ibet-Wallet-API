# -*- coding: utf-8 -*-
import json

from .account_config import eth_account
from app import config
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_payment_gateway, register_exchange_regulator, \
    take_buy_bond_token, get_latest_orderid, \
    membership_issue, membership_offer, membership_get_latest_orderid, \
    membership_take_buy, issue_coupon_token, coupon_offer, \
    coupon_get_latest_orderid, coupon_take_buy, get_latest_agreementid, bond_confirm_agreement, \
    membership_get_latest_agreementid, membership_confirm_agreement, coupon_get_latest_agreementid, \
    coupon_confirm_agreement


# [普通社債]現在値取得API
# /v1/StraightBond/LastPrice/
class TestV1StraightBondLastPrice:
    # テスト対象API
    apiurl = '/v1/StraightBond/LastPrice/'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(bond_exchange, personal_info, payment_gateway):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

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
            'redemptionValue': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。',
            'memo': 'メモ',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'personalInfoAddress': personal_info['address']
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

        # 決済業者オペレーション
        latest_agreementid = get_latest_agreementid(bond_exchange, latest_orderid)
        bond_confirm_agreement(agent, bond_exchange, latest_orderid, latest_agreementid)

        return bond_token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_lastprice_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address':
                '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price':
                0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定が発生していないトークンアドレスを指定した場合
    #  -> 現在値：0円
    def test_lastprice_normal_2(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address':
                '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price':
                0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：1000円で約定
    #  -> 現在値1000円が返却される
    def test_lastprice_normal_3(self, client, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']

        bond_token = TestV1StraightBondLastPrice. \
            generate_agree_event(bond_exchange, personal_info, payment_gateway)

        token_address = bond_token['address']
        request_params = {"address_list": [token_address]}

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': token_address,
            'last_price': 1000
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_lastprice_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address_list': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_lastprice_error_2(self, client):
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
    def test_lastprice_error_3(self, client):
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
    def test_lastprice_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/StraightBond/LastPrice'
        }


# [会員権]現在値取得API
# /v1/Membership/LastPrice/
class TestV1MembershipLastPrice:
    # テスト対象API
    apiurl = '/v1/Membership/LastPrice/'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

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

        # 決済業者オペレーション
        latest_agreementid = membership_get_latest_agreementid(exchange, latest_orderid)
        membership_confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_membership_lastprice_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定が発生していないトークンアドレスを指定した場合
    #  -> 現在値：0円
    def test_membership_lastprice_normal_2(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：1000円で約定
    #  -> 現在値1000円が返却される
    def test_membership_lastprice_normal_3(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']
        token = TestV1MembershipLastPrice.generate_agree_event(exchange)
        token_address = token['address']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        request_params = {"address_list": [token_address]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': token_address,
            'last_price': 1000
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_membership_lastprice_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address_list': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_membership_lastprice_error_2(self, client):
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
    def test_membership_lastprice_error_3(self, client):
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
    def test_membership_lastprice_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/Membership/LastPrice'
        }


# [クーポン]現在値取得API
# /v1/Coupon/LastPrice/
class TestV1CouponLastPrice:
    # テスト対象API
    apiurl = '/v1/Coupon/LastPrice/'

    # 約定イベントの作成
    @staticmethod
    def generate_agree_event(exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

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

        # 決済業者オペレーション
        latest_agreementid = coupon_get_latest_agreementid(exchange, latest_orderid)
        coupon_confirm_agreement(agent, exchange, latest_orderid, latest_agreementid)

        return token

    # 正常系1：存在しない取引コントラクトアドレスを指定
    #  -> 現在値：0円
    def test_coupon_lastprice_normal_1(self, client):
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            "0xe883a6f441ad5682d37df31d34fc012bcb07a740"

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系2：約定が発生していないトークンアドレスを指定した場合
    #  -> 現在値：0円
    def test_coupon_lastprice_normal_2(self, client, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a740"
        request_params = {"address_list": [token_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        resp = client. \
            simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': '0xe883a6f441ad5682d37df31d34fc012bcb07a740',
            'last_price': 0
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系3：1000円で約定
    #  -> 現在値1000円が返却される
    def test_coupon_lastprice_normal_3(self, client, shared_contract):
        exchange = shared_contract['IbetCouponExchange']
        token = TestV1CouponLastPrice.generate_agree_event(exchange)
        token_address = token['address']
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = \
            exchange['address']

        request_params = {"address_list": [token_address]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = [{
            'token_address': token_address,
            'last_price': 1000
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # エラー系1：入力値エラー（request-bodyなし）
    def test_coupon_lastprice_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'address_list': 'required field'
            }
        }

    # エラー系2：入力値エラー（headersなし）
    def test_coupon_lastprice_error_2(self, client):
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
    def test_coupon_lastprice_error_3(self, client):
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
    def test_coupon_lastprice_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/Coupon/LastPrice'
        }
