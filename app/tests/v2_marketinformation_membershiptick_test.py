# -*- coding: utf-8 -*-
import json

from .account_config import eth_account
from app import config
from .contract_modules import membership_issue, membership_offer, \
    membership_get_latest_orderid, membership_take_buy


class TestV2MembershipTick:
    """
    Test Case for v2.market_information.MembershipTick
    """

    # テスト対象API
    apiurl = '/v2/Market/Tick/Membership'

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
        token = TestV2MembershipTick.generate_agree_event(exchange)
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
            'description': 'method: GET, url: /v2/Market/Tick/Membership'
        }
