"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from app import config
from app.tests.account_config import eth_account
from app.tests.contract_modules import issue_bond_token, register_personalinfo, register_payment_gateway, \
    offer_bond_token, get_latest_orderid, take_buy_bond_token, get_latest_agreementid, \
    membership_issue, membership_offer, membership_get_latest_orderid, membership_get_latest_agreementid, \
    membership_take_buy, issue_coupon_token, coupon_offer, coupon_get_latest_orderid, coupon_take_buy, \
    coupon_get_latest_agreementid, issue_share_token, share_offer, share_get_latest_orderid, share_take_buy, \
    share_get_latest_agreementid


class TestV2GetAgreementGet:
    """
    Test Case for v2.market_information.GetAgreement
    """

    # テスト対象API
    apiurl = '/v2/Market/Agreement'

    # 約定イベントの作成（債券）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_bond(exchange, personal_info, payment_gateway):
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

    # 約定イベントの作成（株式）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_share(exchange, personal_info):
        issuer = eth_account['issuer']
        trader = eth_account['trader']

        attribute = {
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'tradableExchange': exchange['address'],
            'personalInfoAddress': personal_info['address'],
            'issuePrice': 1000,
            'totalSupply': 1000000,
            'dividends': 101,
            'dividendRecordDate': '20200401',
            'dividendPaymentDate': '20200502',
            'cancellationDate': '20200603',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'memo': 'メモ',
            'transferable': True
        }

        # ＜発行体オペレーション＞
        #   1) 株式トークン発行
        #   2) 株式トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 募集（Make売）
        token = issue_share_token(issuer, attribute)
        register_personalinfo(issuer, personal_info)
        share_offer(issuer, exchange, token, trader, 100, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) Take買
        register_personalinfo(trader, personal_info)
        latest_orderid = share_get_latest_orderid(exchange)
        share_take_buy(trader, exchange, latest_orderid)
        latest_agreementid = share_get_latest_agreementid(exchange, latest_orderid)

        return token, latest_orderid, latest_agreementid

    # 約定イベントの作成（会員権）
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_membership(exchange):
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
    # 発行体：Make売、投資家：Take買
    @staticmethod
    def _generate_agree_event_coupon(exchange):
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

    ########################################################################################
    # Normal
    ########################################################################################

    # <Normal_1>
    # StraightBond
    def test_normal_1(self, client, shared_contract):
        exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']

        _, order_id, agreement_id = self._generate_agree_event_bond(exchange, personal_info, payment_gateway)

        # 環境変数設定
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange["address"]}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'buyer_address': eth_account['trader']['account_address'],
            'seller_address': eth_account['issuer']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['buyer_address'] == assumed_body['buyer_address']
        assert resp.json['data']['seller_address'] == assumed_body['seller_address']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    # <Normal_2>
    # Membership
    def test_normal_2(self, client, shared_contract):
        exchange = shared_contract['IbetMembershipExchange']

        _, order_id, agreement_id = self._generate_agree_event_membership(exchange)

        # 環境変数設定
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange["address"]}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'buyer_address': eth_account['trader']['account_address'],
            'seller_address': eth_account['issuer']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['buyer_address'] == assumed_body['buyer_address']
        assert resp.json['data']['seller_address'] == assumed_body['seller_address']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    # <Normal_3>
    # Coupon
    def test_normal_3(self, client, shared_contract):
        exchange = shared_contract['IbetCouponExchange']

        _, order_id, agreement_id = self._generate_agree_event_coupon(exchange)

        # 環境変数設定
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange["address"]}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'buyer_address': eth_account['trader']['account_address'],
            'seller_address': eth_account['issuer']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['buyer_address'] == assumed_body['buyer_address']
        assert resp.json['data']['seller_address'] == assumed_body['seller_address']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    # <Normal_4>
    # Share
    def test_normal_4(self, client, shared_contract):
        exchange = shared_contract['IbetOTCExchange']
        personal_info = shared_contract['PersonalInfo']

        _, order_id, agreement_id = self._generate_agree_event_share(exchange, personal_info)

        # 環境変数設定
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange["address"]}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = {
            'amount': 100,
            'canceled': False,
            'counterpart': eth_account['trader']['account_address'],
            'buyer_address': eth_account['trader']['account_address'],
            'seller_address': eth_account['issuer']['account_address'],
            'paid': False,
            'price': 1000
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['amount'] == assumed_body['amount']
        assert resp.json['data']['canceled'] == assumed_body['canceled']
        assert resp.json['data']['counterpart'] == assumed_body['counterpart']
        assert resp.json['data']['buyer_address'] == assumed_body['buyer_address']
        assert resp.json['data']['seller_address'] == assumed_body['seller_address']
        assert resp.json['data']['paid'] == assumed_body['paid']
        assert resp.json['data']['price'] == assumed_body['price']

    ########################################################################################
    # Error
    ########################################################################################

    # Error_1
    # 入力値エラー（query_stringなし）
    # 400
    def test_error_1(self, client):
        query_string = ""
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # Error_2
    # 入力値エラー（exchange_addressの型誤り）
    # 400
    def test_error_2(self, client):
        exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3B'  # アドレス長が短い
        query_string = f'order_id=2&agreement_id=102&exchange_address={exchange_address}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # Error_3
    # 入力値エラー（数値項目の型誤り）
    # 400
    def test_error_3(self, client):
        exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        query_string = f'order_id=aa&agreement_id=bb&exchange_address={exchange_address}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter'
        }

    # Error_4
    # 指定した約定情報が存在しない
    # 400
    def test_error_4(self, client, shared_contract):
        exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']

        _, order_id, agreement_id = self._generate_agree_event_bond(exchange, personal_info, payment_gateway)
        not_exist_order_id = 999
        not_exist_agreement_id = 999

        # 環境変数設定
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = exchange['address']
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None

        query_string = f'order_id={not_exist_order_id}&agreement_id={not_exist_agreement_id}&' \
                       f'exchange_address={exchange["address"]}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Data not found'
        }

    # Error_5
    # exchangeアドレスが環境変数に未設定
    # 400
    def test_error_5(self, client):
        exchange_address = '0x82b1c9374aB625380bd498a3d9dF4033B8A0E3Bb'
        order_id = 2
        agreement_id = 102

        query_string = f'order_id={order_id}&agreement_id={agreement_id}&exchange_address={exchange_address}'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'Invalid Address'
        }
