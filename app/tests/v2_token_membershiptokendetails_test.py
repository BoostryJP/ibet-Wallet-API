# -*- coding: utf-8 -*-
from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model import Listing
from app import config
from app.contracts import Contract

from .account_config import eth_account
from .contract_modules import membership_issue, membership_register_list, membership_invalidate

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


class TestV2TokenMembershipTokenDetails():
    """
    Test Case for v2.token.MembershipTokenDetails
    """

    # テスト対象API
    apiurl_base = '/v2/Token/Membership/' # {contract_address}

    def token_attribute(exchange_address):
        attribute = {
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'initialSupply': 1000000,
            'tradableExchange': exchange_address,
            'details': '詳細',
            'returnDetails': 'リターン詳細',
            'expirationDate': '20191231',
            'memo': 'メモ',
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

    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    # ＜正常系1＞
    #   データあり
    def test_membershipdetails_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenMembershipTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：会員権新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        attribute = TestV2TokenMembershipTokenDetails.token_attribute(exchange_address)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenMembershipTokenDetails.list_token(session, token)

        apiurl = self.apiurl_base + token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'token_address': token['address'],
            'token_template': 'IbetMembership',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト会員権',
            'symbol': 'MEMBERSHIP',
            'total_supply': 1000000,
            'details': '詳細',
            'return_details': 'リターン詳細',
            'expiration_date': '20191231',
            'memo': 'メモ',
            'transferable': True,
            'status': True,
            'initial_offering_status': False,
            'image_url': [
                {'id': 1, 'url': ''},
                {'id': 2, 'url': ''},
                {'id': 3, 'url': ''}
            ],
            'payment_method_credit_card': True,
            'payment_method_bank': True,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー'
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    #   無効なコントラクトアドレス
    #   -> 400エラー
    def test_membershipdetails_error_1(self, client):
        apiurl = self.apiurl_base + '0xabcd'

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
    def test_membershipdetails_error_2(self, client, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenMembershipTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：会員権新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        attribute = TestV2TokenMembershipTokenDetails.token_attribute(exchange_address)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # NOTE:取扱トークンデータを挿入しない

        apiurl = self.apiurl_base + token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + token['address']
        }

    # ＜エラー系3＞
    #   トークン無効化（データなし）
    #   -> 404エラー
    def test_membershipdetails_error_3(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenMembershipTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：会員権新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        attribute = TestV2TokenMembershipTokenDetails. \
            token_attribute(exchange_address)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenMembershipTokenDetails.list_token(session, token)

        # Tokenの無効化
        membership_invalidate(issuer, token)

        apiurl = self.apiurl_base + token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 30,
            'message': 'Data Not Exists',
            'description': 'contract_address: ' + token['address']
        }