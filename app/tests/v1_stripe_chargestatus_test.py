# -*- coding: utf-8 -*-
import pytest
import json
import os

from app.model import StripeCharge, StripeChargeStatus

# [Stripe]課金状態取得
# /v1/Stripe/ChargeStatus
class TestV1StripeChargeStatus():

    # テスト対象API
    apiurl = '/v1/Stripe/ChargeStatus'
    default_exchange_address = '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF'
    default_order_id = 1
    default_agreement_id = 1
    delivery_amount = 1000
    default_request_params = {
        'exchange_address': default_exchange_address,
        'order_id': default_order_id,
        'agreement_id': default_agreement_id
    }

    @staticmethod
    def insert_charge_record(self, session, status, receipt_url):
        # Charge情報を挿入
        stripe_charge = StripeCharge()
        stripe_charge.id = 1
        stripe_charge.exchange_address = self.default_exchange_address
        stripe_charge.order_id = self.default_order_id
        stripe_charge.agreement_id = self.default_agreement_id
        stripe_charge.delivery_amount = self.delivery_amount
        stripe_charge.status = status
        stripe_charge.receipt_url = receipt_url
        session.add(stripe_charge)

    # ＜正常系1＞
    # レコードあり（PENDING）
    def test_stripe_chargestatus_normal_1(self, client, session):
        TestV1StripeChargeStatus.insert_charge_record(self, session, 0, '')

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(self.default_request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            "order_id": 1,
            "agreement_id": 1,
            "delivery_amount": 1000
            "status": "PENDING",
            "receipt_url": ''
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # レコードあり（SUCCEEDED）
    def test_stripe_chargestatus_normal_2(self, client, session):
        TestV1StripeChargeStatus.insert_charge_record(self, session, 1, "https://pay.stripe.com/receipts/acct_1EMvILHgQLLPjBO2/ch_1Eig9bHgQLLPjBO2z5ENiAKy/rcpt_FD6MhF6EpK4IRarTdCK8FTwwrC7r5PE")

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(self.default_request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            "order_id": 1,
            "agreement_id": 1,
            "delivery_amount": 1000,
            "status": "SUCCEEDED",
            "receipt_url":"https://pay.stripe.com/receipts/acct_1EMvILHgQLLPjBO2/ch_1Eig9bHgQLLPjBO2z5ENiAKy/rcpt_FD6MhF6EpK4IRarTdCK8FTwwrC7r5PE"
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    # レコードあり（FAILED）
    def test_stripe_chargestatus_normal_3(self, client, session):
        TestV1StripeChargeStatus.insert_charge_record(self, session, 2, '')

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(self.default_request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            "order_id": 1,
            "agreement_id": 1,
            "delivery_amount": 1000,
            "status": "FAILED",
            "receipt_url": ''
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4＞
    # レコードなし（NONE）
    def test_stripe_chargestatus_normal_4(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(self.default_request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            "order_id": 1,
            "agreement_id": 1,
            "delivery_amount": None
            "status": "NONE",
            "receipt_url": ''
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1-1＞
    # 必須項目なし：exchange_address
    def test_stripe_chargestatus_error_1_1(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'order_id': self.default_order_id,
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'required field'
            }
        }

    # ＜エラー系1-2＞
    # exchange_addressの値が空
    def test_stripe_chargestatus_error_1_2(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': '',
            'order_id': self.default_order_id,
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'empty values not allowed'
            }
        }

    # ＜エラー系1-3＞
    # exchange_addressの値が数字
    def test_stripe_chargestatus_error_1_3(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': 1234,
            'order_id': self.default_order_id,
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'exchange_address': 'must be of string type'
            }
        }

    # ＜エラー系1-4＞
    # exchange_addressのアドレスフォーマットが誤り
    def test_stripe_chargestatus_error_1_4(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': "0x2B5AD5c4795c026514f8317c7a215E218DcCD6c", # 短い,
            'order_id': self.default_order_id,
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'invalid exchange address'
        }

    # ＜エラー系2-1＞
    # 必須項目なし：order_id
    def test_stripe_chargestatus_error_2_1(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_id': 'required field'
            }
        }

    # ＜エラー系2-2＞
    # order_idの値がNull
    def test_stripe_chargestatus_error_2_2(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF',
            'order_id': None,
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_id': [
                    'null value not allowed',
                    "field 'order_id' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-3＞
    # order_idの値がマイナス値
    def test_stripe_chargestatus_error_2_3(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF',
            'order_id': -1,
            'agreement_id': self.default_agreement_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'order_id': 'min value is 0'
            }
        }

    # ＜エラー系3-1＞
    # 必須項目なし：agreement_id
    def test_stripe_chargestatus_error_3_1(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            "exchange_address": "0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF",
            'order_id': self.default_order_id
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agreement_id': 'required field'
            }
        }

    # ＜エラー系3-2＞
    # agreement_idの値がNull
    def test_stripe_chargestatus_error_3_2(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF',
            'order_id': self.default_order_id,
            'agreement_id': None
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agreement_id': [
                    'null value not allowed',
                    "field 'agreement_id' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系3-3＞
    # agreement_idの値がマイナス値
    def test_stripe_chargestatus_error_3_3(self, client, session):
        headers = {'Content-Type': 'application/json'}
        request_params = {
            'exchange_address': '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF',
            'order_id': self.default_order_id,
            'agreement_id': -1
        }
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] ==  {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'agreement_id': 'min value is 0'
            }
        }
