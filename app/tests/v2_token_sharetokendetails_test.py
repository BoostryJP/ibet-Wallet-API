# -*- coding: utf-8 -*-
from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model import Listing
from app import config
from app.contracts import Contract

from .account_config import eth_account
from .contract_modules import issue_share_token, register_share_list, register_share_reference_url

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


class TestV2TokenShareTokenDetails:
    """
    Test Case for v2.token.ShareTokenDetails
    """

    # テスト対象API
    apiurl_base = '/v2/Token/Share/'  # {contract_address}

    @staticmethod
    def share_token_attribute(exchange_address, personal_info_address):
        attribute = {
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'tradableExchange': exchange_address,
            'personalInfoAddress': personal_info_address,
            'totalSupply': 1000000,
            'issuePrice': 10000,
            'dividends': 101,
            'dividendRecordDate': '20200909',
            'dividendPaymentDate': '20201001',
            'cancellationDate': '20210101',
            'contactInformation': '問い合わせ先',
            'privacyPolicy': 'プライバシーポリシー',
            'memo': 'メモ',
            'transferable': True
        }
        return attribute

    @staticmethod
    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal.unlockAccount(deployer['account_address'], deployer['password'])

        contract_address, abi = Contract.deploy_contract('TokenList', [], deployer['account_address'])

        return {'address': contract_address, 'abi': abi}

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        listed_token.payment_method_credit_card = True
        listed_token.payment_method_bank = True
        session.add(listed_token)

    # ＜正常系1＞
    #   データあり
    def test_sharedetails_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenShareTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：株式新規発行
        exchange_address = to_checksum_address(shared_contract['IbetOTCExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = TestV2TokenShareTokenDetails.share_token_attribute(exchange_address, personal_info)
        share_token = issue_share_token(issuer, attribute)
        url_list = ['http://hogehoge/1', 'http://hogehoge/2', 'http://hogehoge/3']
        register_share_reference_url(issuer, share_token, url_list)
        register_share_list(issuer, share_token, token_list)

        # 取扱トークンデータ挿入
        TestV2TokenShareTokenDetails.list_token(session, share_token)

        apiurl = self.apiurl_base + share_token['address']
        query_string = ''
        resp = client.simulate_get(apiurl, query_string=query_string)

        assumed_body = {
            'token_address': share_token['address'],
            'token_template': 'IbetShare',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'total_supply': 1000000,
            'issue_price': 10000,
            'dividend_information': {
                'dividends': 1.01,
                'dividend_record_date': '20200909',
                'dividend_payment_date': '20201001'
            },
            'cancellation_date': '20210101',
            'reference_urls': [
                {'id': 1, 'url': 'http://hogehoge/1'},
                {'id': 2, 'url': 'http://hogehoge/2'},
                {'id': 3, 'url': 'http://hogehoge/3'}
            ],
            'image_url': [],
            'offering_status': False,
            'memo':  'メモ',
            'max_holding_quantity': 1,
            'max_sell_amount': 1000,
            'payment_method_credit_card': True,
            'payment_method_bank': True,
            'contact_information': '問い合わせ先',
            'privacy_policy': 'プライバシーポリシー',
            'transferable': True,
            'status': True
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    #   無効なコントラクトアドレス
    #   -> 400エラー
    def test_sharedetails_error_1(self, client):
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
    def test_sharedetails_error_2(self, client, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV2TokenShareTokenDetails.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行
        exchange_address = to_checksum_address(shared_contract['IbetOTCExchange']['address'])
        personal_info = to_checksum_address(shared_contract['PersonalInfo']['address'])
        attribute = TestV2TokenShareTokenDetails.share_token_attribute(exchange_address, personal_info)
        token = issue_share_token(issuer, attribute)
        register_share_list(issuer, token, token_list)

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