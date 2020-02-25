# -*- coding: utf-8 -*-
import json

from app import config
from app.model import Listing, PrivateListing

from .account_config import eth_account
from .contract_modules import issue_bond_token, offer_bond_token, \
    register_personalinfo, register_payment_gateway, take_buy_bond_token, get_latest_orderid, \
    register_bond_list, get_latest_agreementid, bond_confirm_agreement


class TestV2StraightBondMyTokens:
    """
    Test Case for v2.position.StraightBondMyTokens
    """

    # テスト対象API
    apiurl = '/v2/Position/StraightBond'

    # 債券トークンの保有状態（約定イベント）を作成
    @staticmethod
    def generate_bond_position(bond_exchange, personal_info,
                               payment_gateway, token_list):
        issuer = eth_account['issuer']
        trader = eth_account['trader']
        agent = eth_account['agent']

        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': bond_exchange['address'],
            'faceValue': 10000,
            'interestRate': 602,
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
            'personalInfoAddress': personal_info['address'],
            'transferable': True,
            'isRedeemed': False
        }

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
        latest_orderid = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, latest_orderid, 100)

        # ＜決済業者オペレーション＞
        latest_agreementid = get_latest_agreementid(bond_exchange, latest_orderid)
        bond_confirm_agreement(agent, bond_exchange, latest_orderid, latest_agreementid)

        return bond_token

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.id = 1
        listed_token.token_address = token['address']
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    @staticmethod
    def list_private_token(session, token):
        listed_token = PrivateListing()
        listed_token.id = 1
        listed_token.token_address = token['address']
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    # ＜正常系1＞
    # 債券トークン保有
    #  債券新規発行 -> 約定（1件）
    #   -> 該当債券の預かりが返却
    def test_position_normal_1(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        bond_token = TestV2StraightBondMyTokens.generate_bond_position(
            bond_exchange, personal_info, payment_gateway, token_list)
        token_address = bond_token['address']

        # 取扱トークンデータ挿入
        TestV2StraightBondMyTokens.list_token(session, bond_token)

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'total_supply': 1000000,
                'face_value': 10000,
                'interest_rate': 0.0602,
                'interest_payment_date1': '0101',
                'interest_payment_date2': '0201',
                'interest_payment_date3': '0301',
                'interest_payment_date4': '0401',
                'interest_payment_date5': '0501',
                'interest_payment_date6': '0601',
                'interest_payment_date7': '0701',
                'interest_payment_date8': '0801',
                'interest_payment_date9': '0901',
                'interest_payment_date10': '1001',
                'interest_payment_date11': '1101',
                'interest_payment_date12': '1201',
                'redemption_date': '20191231',
                'redemption_value': 10000,
                'return_date': '20191231',
                'return_amount': '商品券をプレゼント',
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
                'certification': [],
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'transferable': True,
                'isRedeemed': False
            },
            'balance': 100,
            'commitment': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # ＜正常系2＞
    # 債券トークン保有
    #  未公開トークンリストの場合
    def test_position_normal_2(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        bond_token = TestV2StraightBondMyTokens.generate_bond_position(
            bond_exchange, personal_info, payment_gateway, token_list)
        token_address = bond_token['address']

        # 取扱トークンデータ挿入
        TestV2StraightBondMyTokens.list_private_token(session, bond_token)

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'total_supply': 1000000,
                'face_value': 10000,
                'interest_rate': 0.0602,
                'interest_payment_date1': '0101',
                'interest_payment_date2': '0201',
                'interest_payment_date3': '0301',
                'interest_payment_date4': '0401',
                'interest_payment_date5': '0501',
                'interest_payment_date6': '0601',
                'interest_payment_date7': '0701',
                'interest_payment_date8': '0801',
                'interest_payment_date9': '0901',
                'interest_payment_date10': '1001',
                'interest_payment_date11': '1101',
                'interest_payment_date12': '1201',
                'redemption_date': '20191231',
                'redemption_value': 10000,
                'return_date': '20191231',
                'return_amount': '商品券をプレゼント',
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
                'certification': [],
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'transferable': True,
                'isRedeemed': False
            },
            'balance': 100,
            'commitment': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # ＜正常系3＞
    # 債券トークン保有
    #  特殊系：公開トークンと未公開トークンが重複
    def test_position_normal_3(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        bond_token = TestV2StraightBondMyTokens.generate_bond_position(
            bond_exchange, personal_info, payment_gateway, token_list)
        token_address = bond_token['address']

        # 取扱トークンデータ挿入
        TestV2StraightBondMyTokens.list_private_token(session, bond_token)
        TestV2StraightBondMyTokens.list_token(session, bond_token)

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            'token': {
                'token_address': token_address,
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'total_supply': 1000000,
                'face_value': 10000,
                'interest_rate': 0.0602,
                'interest_payment_date1': '0101',
                'interest_payment_date2': '0201',
                'interest_payment_date3': '0301',
                'interest_payment_date4': '0401',
                'interest_payment_date5': '0501',
                'interest_payment_date6': '0601',
                'interest_payment_date7': '0701',
                'interest_payment_date8': '0801',
                'interest_payment_date9': '0901',
                'interest_payment_date10': '1001',
                'interest_payment_date11': '1101',
                'interest_payment_date12': '1201',
                'redemption_date': '20191231',
                'redemption_value': 10000,
                'return_date': '20191231',
                'return_amount': '商品券をプレゼント',
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
                'certification': [],
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'transferable': True,
                'isRedeemed': False
            },
            'balance': 100,
            'commitment': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address:
                count = 1
                assert token == assumed_body
        assert count == 1

    # ＜正常系4＞
    # 複数保有
    #  公開トークンと未公開トークンの複数保有
    def test_position_normal_4(self, client, session, shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']

        account = eth_account['trader']
        request_params = {"account_address_list": [account['account_address']]}

        # トークン①
        bond_token_1 = TestV2StraightBondMyTokens.generate_bond_position(
            bond_exchange, personal_info, payment_gateway, token_list)
        token_address_1 = bond_token_1['address']

        # トークン②
        bond_token_2 = TestV2StraightBondMyTokens.generate_bond_position(
            bond_exchange, personal_info, payment_gateway, token_list)
        token_address_2 = bond_token_2['address']


        # 取扱トークンデータ挿入
        TestV2StraightBondMyTokens.list_private_token(session, bond_token_1)
        TestV2StraightBondMyTokens.list_token(session, bond_token_2)

        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(self.apiurl, headers=headers, body=request_body)

        assumed_body_1 = {
            'token': {
                'token_address': token_address_1,
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'total_supply': 1000000,
                'face_value': 10000,
                'interest_rate': 0.0602,
                'interest_payment_date1': '0101',
                'interest_payment_date2': '0201',
                'interest_payment_date3': '0301',
                'interest_payment_date4': '0401',
                'interest_payment_date5': '0501',
                'interest_payment_date6': '0601',
                'interest_payment_date7': '0701',
                'interest_payment_date8': '0801',
                'interest_payment_date9': '0901',
                'interest_payment_date10': '1001',
                'interest_payment_date11': '1101',
                'interest_payment_date12': '1201',
                'redemption_date': '20191231',
                'redemption_value': 10000,
                'return_date': '20191231',
                'return_amount': '商品券をプレゼント',
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
                'certification': [],
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'transferable': True,
                'isRedeemed': False
            },
            'balance': 100,
            'commitment': 0
        }

        assumed_body_2 = {
            'token': {
                'token_address': token_address_2,
                'token_template': 'IbetStraightBond',
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト債券',
                'symbol': 'BOND',
                'total_supply': 1000000,
                'face_value': 10000,
                'interest_rate': 0.0602,
                'interest_payment_date1': '0101',
                'interest_payment_date2': '0201',
                'interest_payment_date3': '0301',
                'interest_payment_date4': '0401',
                'interest_payment_date5': '0501',
                'interest_payment_date6': '0601',
                'interest_payment_date7': '0701',
                'interest_payment_date8': '0801',
                'interest_payment_date9': '0901',
                'interest_payment_date10': '1001',
                'interest_payment_date11': '1101',
                'interest_payment_date12': '1201',
                'redemption_date': '20191231',
                'redemption_value': 10000,
                'return_date': '20191231',
                'return_amount': '商品券をプレゼント',
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
                'certification': [],
                'initial_offering_status': False,
                'max_holding_quantity': 1,
                'max_sell_amount': 1000,
                'payment_method_credit_card': True,
                'payment_method_bank': True,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'transferable': True,
                'isRedeemed': False
            },
            'balance': 100,
            'commitment': 0
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}

        count = 0
        for token in resp.json['data']:
            if token['token']['token_address'] == token_address_1:
                count += 1
                assert token == assumed_body_1
            if token['token']['token_address'] == token_address_2:
                count += 1
                assert token == assumed_body_2
        assert count == 2


    # エラー系1：入力値エラー（request-bodyなし）
    def test_position_error_1(self, client):
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

    # エラー系2：入力値エラー（headersなし）
    def test_position_error_2(self, client):
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

    # エラー系3-1：入力値エラー（account_addressがアドレスフォーマットではない）
    def test_position_error_3_1(self, client):
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
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

    # エラー系3-2：入力値エラー（account_addressがstring以外）
    def test_position_error_3_2(self, client):
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
