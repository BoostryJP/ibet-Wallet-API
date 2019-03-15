# -*- coding: utf-8 -*-
import pytest
import json
import os

from app.model import Order, Agreement, AgreementStatus

from .account_config import eth_account
from .contract_modules import *


# 注文一覧・約定一覧API（普通社債）
# /v1/OrderList/
class TestV1OrderList_Bond():

    # テスト対象API
    apiurl = '/v1/OrderList/'

    def bond_token_attribute(exchange):
        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange['address'],
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
            'memo': 'メモ'
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account['issuer']

        attribute = TestV1OrderList_Bond.bond_token_attribute(bond_exchange)

        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) 募集
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        order_id = get_latest_orderid(bond_exchange) - 1
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList_Bond.bond_token_attribute(bond_exchange)

        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) 募集
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) 収納代行コントラクト（PaymentGateway）に投資家の情報を登録
        #   3) 買い注文
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        order_id = get_latest_orderid(bond_exchange) - 1
        take_buy_bond_token(trader, bond_exchange, order_id, 100)
        agreement_id = get_latest_agreementid(bond_exchange, order_id) - 1

        return bond_token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList_Bond.bond_token_attribute(bond_exchange)

        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) 募集
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) 収納代行コントラクト（PaymentGateway）に投資家の情報を登録
        #   3) 買い注文
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        order_id = get_latest_orderid(bond_exchange) - 1
        take_buy_bond_token(trader, bond_exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = get_latest_agreementid(bond_exchange, order_id) - 1
        bond_confirm_agreement(agent, bond_exchange, order_id, agreement_id)

        return bond_token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        membership_exchange = shared_contract['IbetMembershipExchange']
        coupon_exchange = shared_contract['IbetCouponExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']
        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = \
            bond_exchange['address']
        os.environ["IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS"] = \
            membership_exchange['address']
        os.environ["IBET_CP_EXCHANGE_CONTRACT_ADDRESS"] = \
            coupon_exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']
        return bond_exchange, membership_exchange, coupon_exchange, \
            personal_info, payment_gateway, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_orderlist_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, \
            personal_info, payment_gateway, token_list = \
                TestV1OrderList_Bond.set_env(shared_contract)

        bond_token, order_id, agreement_id = TestV1OrderList_Bond.order_event(
            bond_exchange, personal_info, payment_gateway, token_list)

        account = eth_account['issuer']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = bond_token['address']
        order.exchange_address = bond_exchange['address']
        order.order_id = order_id
        order.unique_order_id = bond_exchange['address'] + '_' + str(1)
        order.account_address = account['account_address']
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account['agent']['account_address']
        order.is_cancelled = False
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': bond_token['address'],
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
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
                'image_url': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'certification': []
            },
            'order': {
                'order_id': order_id,
                'amount': 1000000,
                'price': 1000,
                'isBuy': False,
                'canceled': False
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['order_list']:
            if order['token']['token_address'] == bond_token['address']:
                assert order['token'] == assumed_body['token']
                assert order['order'] == assumed_body['order']

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_orderlist_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, \
            personal_info, payment_gateway, token_list = \
                TestV1OrderList_Bond.set_env(shared_contract)

        bond_token, order_id, agreement_id = TestV1OrderList_Bond.agreement_event(
            bond_exchange, personal_info, payment_gateway, token_list)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = bond_exchange['address']
        agreement.unique_order_id = bond_exchange['address'] + '_' + str(1)
        agreement.buyer_address = account['account_address']
        agreement.seller_address = ''
        agreement.counterpart_address = ''
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': bond_token['address'],
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
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
                'image_url': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'certification': []
            },
            'agreement': {
                'exchange_address': bond_exchange['address'],
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True,
                'canceled': False
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['settlement_list']:
            if order['token']['token_address'] == bond_token['address']:
                assert order['token'] == assumed_body['token']
                assert order['agreement'] == assumed_body['agreement']

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_orderlist_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, \
            personal_info, payment_gateway, token_list = \
                TestV1OrderList_Bond.set_env(shared_contract)

        bond_token, order_id, agreement_id = \
            TestV1OrderList_Bond.settlement_event(
                bond_exchange, personal_info, payment_gateway, token_list)

        token_address = bond_token['address']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = bond_exchange['address']
        agreement.unique_order_id = bond_exchange['address'] + '_' + str(1)
        agreement.buyer_address = account['account_address']
        agreement.seller_address = ''
        agreement.counterpart_address = ''
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': bond_token['address'],
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
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
                'image_url': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }],
                'certification': []
            },
            'agreement': {
                'exchange_address': bond_exchange['address'],
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['complete_list']:
            if order['token']['token_address'] == bond_token['address']:
                assert order['token'] == assumed_body['token']
                assert order['agreement'] == assumed_body['agreement']

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_orderlist_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': 'required field'
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_orderlist_error_2(self, client):
        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_orderlist_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  #アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_orderlist_error_3_2(self, client):
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_orderlist_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/OrderList'
        }

# 注文一覧・約定一覧API（会員権）
# /v1/OrderList/
class TestV1OrderList_Membership():

    # テスト対象API
    apiurl = '/v1/OrderList/'

    def membership_token_attribute(exchange):
        attribute = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
            'transferable': True
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(exchange, token_list):
        issuer = eth_account['issuer']

        attribute = TestV1OrderList_Membership.\
            membership_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        order_id = membership_get_latest_orderid(exchange) - 1
        agreement_id = membership_get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList_Membership.\
            membership_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = membership_get_latest_orderid(exchange) - 1
        membership_take_buy(trader, exchange, order_id, 100)
        agreement_id = membership_get_latest_agreementid(exchange, order_id) - 1

        return token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList_Membership.\
            membership_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = membership_get_latest_orderid(exchange) - 1
        membership_take_buy(trader, exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = membership_get_latest_agreementid(exchange, order_id) - 1
        membership_confirm_agreement(agent, exchange, order_id, agreement_id)

        return token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        membership_exchange = shared_contract['IbetMembershipExchange']
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']
        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = \
            bond_exchange['address']
        os.environ["IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS"] = \
            membership_exchange['address']
        os.environ["IBET_CP_EXCHANGE_CONTRACT_ADDRESS"] = \
            coupon_exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']
        return bond_exchange, membership_exchange, coupon_exchange, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_membership_orderlist_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            TestV1OrderList_Membership.set_env(shared_contract)

        token, order_id, agreement_id = \
            TestV1OrderList_Membership.order_event(membership_exchange, token_list)

        account = eth_account['issuer']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = token['address']
        order.exchange_address = membership_exchange['address']
        order.order_id = 1
        order.unique_order_id = membership_exchange['address'] + '_' + str(1)
        order.account_address = account['account_address']
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account['agent']['account_address']
        order.is_cancelled = False
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token['address'],
                'token_template': 'IbetMembership',
                'company_name': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ]
            },
            'order': {
                'order_id': order_id,
                'amount': 1000000,
                'price': 1000,
                'isBuy': False,
                'canceled': False
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、order_listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['order_list']:
            if order['token']['token_address'] == token['address']:
                assert order['token'] == assumed_body['token']
                assert order['order'] == assumed_body['order']

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_membership_orderlist_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            TestV1OrderList_Membership.set_env(shared_contract)

        token, order_id, agreement_id = \
            TestV1OrderList_Membership.agreement_event(
                membership_exchange, token_list)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = membership_exchange['address']
        agreement.unique_order_id = membership_exchange['address'] + '_' + str(1)
        agreement.buyer_address = account['account_address']
        agreement.seller_address = ''
        agreement.counterpart_address = ''
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token['address'],
                'token_template': 'IbetMembership',
                'company_name': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'image_url': [{
                    'id': 1,
                    'url': ''
                }, {
                    'id': 2,
                    'url': ''
                }, {
                    'id': 3,
                    'url': ''
                }]
            },
            'agreement': {
                'exchange_address': membership_exchange['address'],
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True,
                'canceled': False
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['settlement_list']:
            if order['token']['token_address'] == token['address']:
                assert order['token'] == assumed_body['token']
                assert order['agreement'] == assumed_body['agreement']

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_membership_orderlist_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            TestV1OrderList_Membership.set_env(shared_contract)

        token, order_id, agreement_id = \
            TestV1OrderList_Membership.settlement_event(membership_exchange, token_list)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = membership_exchange['address']
        agreement.unique_order_id = membership_exchange['address'] + '_' + str(1)
        agreement.buyer_address = account['account_address']
        agreement.seller_address = ''
        agreement.counterpart_address = ''
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token['address'],
                'token_template': 'IbetMembership',
                'company_name': '',
                'name': 'テスト会員権',
                'symbol': 'MEMBERSHIP',
                'total_supply': 1000000,
                'details': '詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'メモ',
                'transferable': True,
                'status': True,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ]
            },
            'agreement': {
                'exchange_address': membership_exchange['address'],
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['complete_list']:
            if order['token']['token_address'] == token['address']:
                assert order['token'] == assumed_body['token']
                assert order['agreement'] == assumed_body['agreement']

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_membership_orderlist_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': 'required field'
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_membership_orderlist_error_2(self, client):
        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_membership_orderlist_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  #アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_membership_orderlist_error_3_2(self, client):
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_membership_orderlist_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/OrderList'
        }

# 注文一覧・約定一覧API（クーポン）
# /v1/OrderList/
class TestV1OrderList_Coupon():

    # テスト対象API
    apiurl = '/v1/OrderList/'

    def coupon_token_attribute(exchange):
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
            'tradableExchange': exchange['address'],
            'details': 'クーポン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(exchange, token_list):
        issuer = eth_account['issuer']

        attribute = TestV1OrderList_Coupon.coupon_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        order_id = coupon_get_latest_orderid(exchange) - 1
        agreement_id = coupon_get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList_Coupon.coupon_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = coupon_get_latest_orderid(exchange) - 1
        coupon_take_buy(trader, exchange, order_id, 100)
        agreement_id = coupon_get_latest_agreementid(exchange, order_id) - 1

        return token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(exchange, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = TestV1OrderList_Coupon.coupon_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = coupon_get_latest_orderid(exchange) - 1
        coupon_take_buy(trader, exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = coupon_get_latest_agreementid(exchange, order_id) - 1
        coupon_confirm_agreement(agent, exchange, order_id, agreement_id)

        return token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        membership_exchange = shared_contract['IbetMembershipExchange']
        coupon_exchange = shared_contract['IbetCouponExchange']
        token_list = shared_contract['TokenList']
        os.environ["IBET_SB_EXCHANGE_CONTRACT_ADDRESS"] = \
            bond_exchange['address']
        os.environ["IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS"] = \
            membership_exchange['address']
        os.environ["IBET_CP_EXCHANGE_CONTRACT_ADDRESS"] = \
            coupon_exchange['address']
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']
        return bond_exchange, membership_exchange, coupon_exchange, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_coupon_orderlist_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            TestV1OrderList_Coupon.set_env(shared_contract)

        token, order_id, agreement_id = \
            TestV1OrderList_Coupon.order_event(coupon_exchange, token_list)

        account = eth_account['issuer']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = token['address']
        order.exchange_address = coupon_exchange['address']
        order.order_id = 1
        order.unique_order_id = coupon_exchange['address'] + '_' + str(1)
        order.account_address = account['account_address']
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account['agent']['account_address']
        order.is_cancelled = False
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token['address'],
                'token_template': 'IbetCoupon',
                'company_name': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'expiration_date': '20191231',
                'memo': 'クーポンメモ欄',
                'transferable': True,
                'is_valid': True,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ]
            },
            'order': {
                'order_id': order_id,
                'amount': 1000000,
                'price': 1000,
                'isBuy': False,
                'canceled': False
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、order_listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['order_list']:
            if order['token']['token_address'] == token['address']:
                assert order['token'] == assumed_body['token']
                assert order['order'] == assumed_body['order']

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_coupon_orderlist_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            TestV1OrderList_Membership.set_env(shared_contract)

        token, order_id, agreement_id = \
            TestV1OrderList_Coupon.agreement_event(coupon_exchange, token_list)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = coupon_exchange['address']
        agreement.unique_order_id = coupon_exchange['address'] + '_' + str(1)
        agreement.buyer_address = account['account_address']
        agreement.seller_address = ''
        agreement.counterpart_address = ''
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token['address'],
                'token_template': 'IbetCoupon',
                'company_name': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'expiration_date': '20191231',
                'memo': 'クーポンメモ欄',
                'transferable': True,
                'is_valid': True,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ]
            },
            'agreement': {
                'exchange_address': coupon_exchange['address'],
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True,
                'canceled': False
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['settlement_list']:
            if order['token']['token_address'] == token['address']:
                assert order['token'] == assumed_body['token']
                assert order['agreement'] == assumed_body['agreement']

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_coupon_orderlist_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            TestV1OrderList_Coupon.set_env(shared_contract)

        token, order_id, agreement_id = \
            TestV1OrderList_Coupon.settlement_event(coupon_exchange, token_list)

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = coupon_exchange['address']
        agreement.unique_order_id = coupon_exchange['address'] + '_' + str(1)
        agreement.buyer_address = account['account_address']
        agreement.seller_address = ''
        agreement.counterpart_address = ''
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token['address'],
                'token_template': 'IbetCoupon',
                'company_name': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'expiration_date': '20191231',
                'memo': 'クーポンメモ欄',
                'transferable': True,
                'is_valid': True,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ]
            },
            'agreement': {
                'exchange_address': coupon_exchange['address'],
                'order_id': order_id,
                'agreementId': agreement_id,
                'amount': 100,
                'price': 1000,
                'isBuy': True
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        for order in resp.json['data']['complete_list']:
            if order['token']['token_address'] == token['address']:
                assert order['token'] == assumed_body['token']
                assert order['agreement'] == assumed_body['agreement']

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_coupon_orderlist_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': 'required field'
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_coupon_orderlist_error_2(self, client):
        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_coupon_orderlist_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  #アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_coupon_orderlist_error_3_2(self, client):
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'account_address_list': {
                    '0': 'must be of string type'
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_coupon_orderlist_error_4(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v1/OrderList'
        }
