# -*- coding: utf-8 -*-
import json

from app import config
from app.model import Agreement
from app.tests.account_config import eth_account
from app.tests.contract_modules import issue_bond_token, register_personalinfo, register_payment_gateway, \
    offer_bond_token, get_latest_orderid, take_buy_bond_token, get_latest_agreementid, \
    membership_issue, membership_offer, membership_get_latest_orderid, membership_get_latest_agreementid, \
    membership_take_buy, issue_coupon_token, coupon_offer, coupon_get_latest_orderid, coupon_take_buy, \
    coupon_get_latest_agreementid


class TestV2GetAgreement:
    """
    Test Case for v2.market_information.GetAgreement
    """

    # テスト対象API
    apiurl = '/v2/Market/Agreement'

    # 約定イベントの作成（債券）
    def _generate_agree_event_bond(self, exchange, personal_info, payment_gateway):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

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
        token = issue_bond_token(issuer, attribute)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        latest_orderid = get_latest_orderid(exchange)
        take_buy_bond_token(trader, exchange, latest_orderid, 100)
        latest_agreementid = get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定イベントの作成（会員権）
    def _generate_agree_event_membership(self, exchange):
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
        latest_agreementid = membership_get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定イベントの作成（クーポン）
    def _generate_agree_event_coupon(self, exchange):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
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
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # 投資家オペレーション
        latest_orderid = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, latest_orderid, 100)
        latest_agreementid = coupon_get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定情報の挿入
    def _indexer_agreement(self, session, exchange, order_id, agreement_id):
        self.session = session

        # Agreement Record
        a = Agreement()
        a.order_id = order_id
        a.agreement_id = agreement_id
        a.exchange_address = exchange['address']
        a.unique_order_id = exchange['address'] + "_" + str(order_id)
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.amount = 3
        a.status = 0
        a.settlement_timestamp = '2019-11-13 16:23:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

        a = Agreement()
        a.order_id = 2
        a.agreement_id = 102
        a.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.unique_order_id = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb' + "_" + str(2)
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.amount = 3
        a.status = 0
        a.settlement_timestamp = '2019-11-13 16:24:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

        a = Agreement()
        a.order_id = order_id
        a.agreement_id = agreement_id
        a.exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'  # NOTE: Exchangeアドレスのみ異なる
        a.unique_order_id = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb' + "_" + str(1)
        a.buyer_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.seller_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        a.amount = 3
        a.status = 0
        a.settlement_timestamp = '2019-11-13 16:23:14.183706'
        a.created = '2019-11-13 16:26:14.183706'
        session.add(a)

    ########################################################################################
    # Normal
    ########################################################################################

    # <Normal_1>
    # StraightBond
    def test_normal_1(self, client, session, shared_contract):
        exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']

        _, order_id, agreement_id = self._generate_agree_event_bond(exchange, personal_info, payment_gateway)
        self._indexer_agreement(session, exchange, order_id, agreement_id)
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        request_params = {
            "order_id": order_id,
            "agreement_id": agreement_id,
            "exchange_address": exchange['address']
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    # <Normal_2>
    # Membership
    def test_normal_2(self, client, session, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']

        _, order_id, agreement_id = self._generate_agree_event_membership(exchange)
        self._indexer_agreement(session, exchange, order_id, agreement_id)
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        request_params = {
            "order_id": order_id,
            "agreement_id": agreement_id,
            "exchange_address": exchange['address']
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    # <Normal_3>
    # Coupon
    def test_normal_3(self, client, session, shared_contract):
        exchange = shared_contract['IbetCouponExchange']

        _, order_id, agreement_id = self._generate_agree_event_coupon(exchange)
        self._indexer_agreement(session, exchange, order_id, agreement_id)
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']

        request_params = {
            "order_id": order_id,
            "agreement_id": agreement_id,
            "exchange_address": exchange['address']
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    ########################################################################################
    # Error
    ########################################################################################

    # Error_1
    # 入力値エラー（request-bodyなし）
    # 400
    def test_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})
        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'required field',
                'agreement_id': 'required field',
                'order_id': 'required field'
            }
        }

    # Error_2
    # 入力値エラー（headersなし）
    # 400
    def test_tick_error_2(self, client):
        request_params = {
            'exchange_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
            'order_id': 2,
            'agreement_id': 102
        }
        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # Error_3
    # 入力値エラー（exchange_addressの型誤り）
    # 400
    def test_tick_error_3(self, client):
        request_params = {
            'exchange_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3B',  # アドレス長が短い
            'order_id': 2,
            'agreement_id': 102
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # Error_4
    # 指定した約定情報が存在しない
    # 400
    def test_tick_error_4(self, client):
        request_params = {
            'exchange_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
            'order_id': 999,
            'agreement_id': 102
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Data not found'
        }

    # Error_5
    # 指定した約定情報が存在しない
    # 400
    def test_tick_error_5(self, session, client):
        request_params = {
            'exchange_address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb',
            'order_id': 2,
            'agreement_id': 102
        }
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        self._indexer_agreement(
            session,
            {'address': '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'},
            2, 102
        )

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid Address'
        }

    # Error_6
    # HTTPメソッドがサポート外
    # 404
    def test_tick_error_6(self, client):
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: GET, url: /v2/Market/Agreement'
        }
