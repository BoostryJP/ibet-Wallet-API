# -*- coding: utf-8 -*-
from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model import Listing
from app import config
from app.contracts import Contract

from .account_config import eth_account
from .contract_modules import issue_coupon_token, coupon_register_list, invalidate_coupon_token

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


class TestV2TokenCouponTokenStatus:
    """
    Test Case for v2.token.CouponTokenStatus
    """

    # テスト対象API
    apiurl_base = '/v2/Token/Coupon/{contract_address}/Status'

    @staticmethod
    def token_attribute(exchange_address):
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': exchange_address,
            'details': 'クーポン詳細',
            'returnDetails': 'リターン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True,
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー'
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal. \
            unlockAccount(deployer['account_address'], deployer['password'])
        contract_address, abi = Contract. \
            deploy_contract('TokenList', [], deployer['account_address'])
        return {'address': contract_address, 'abi': abi}

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    # ＜正常系1＞
    #   データあり（取扱ステータス = True）
    def test_couponstatus_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokenStatus.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenCouponTokenStatus.list_token(session, token)

        apiurl = self.apiurl_base.format(contract_address=token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'status': True
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    #   データ有り（トークン無効化済み）
    def test_couponstatus_normal_2(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokenStatus.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenCouponTokenStatus.list_token(session, token)

        # Tokenの無効化
        invalidate_coupon_token(issuer, token)

        apiurl = self.apiurl_base.format(contract_address=token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'status': False
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    #   無効なコントラクトアドレス
    #   -> 400エラー
    def test_couponstatus_error_1(self, client):
        apiurl = self.apiurl_base.format(contract_address='0xabcd')

        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'invalid contract_address'
        }

    # ＜エラー系2＞
    #   取扱トークン（DB）に情報が存在しない
    def test_couponstatus_error_2(self, client, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenCouponTokenStatus.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV2TokenCouponTokenStatus.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # NOTE:取扱トークンデータを挿入しない

        apiurl = self.apiurl_base.format(contract_address=token['address'])
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + token['address']
        }
