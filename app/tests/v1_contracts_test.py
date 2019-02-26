# -*- coding: utf-8 -*-
import json
import os
import time
import sys

from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model import Listing
from app import config
from app.contracts import Contract

from .account_config import eth_account
from .contract_modules import issue_bond_token, register_bond_list,\
    membership_issue, membership_register_list, membership_invalidate,\
    issue_coupon_token, coupon_register_list, invalidate_coupon_token

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

# [普通社債]トークン一覧参照API
# /v1/StraightBond/Contracts
class TestV1StraightBondContracts():

    # テスト対象API
    apiurl = '/v1/StraightBond/Contracts/'

    def bond_token_attribute(exchange_address):
        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange_address,
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

    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal.unlockAccount(deployer['account_address'],deployer['password'])

        contract_address, abi = Contract.deploy_contract(
            'TokenList', [], deployer['account_address'])

        return {'address':contract_address, 'abi':abi}

    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.credit_card_availability = True
        listed_token.bank_payment_availability = True
        session.add(listed_token)

    # ＜正常系1＞
    # 発行済債券あり（1件）
    # cursor=設定なし、 limit=設定なし
    # -> 1件返却
    def test_contracts_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1StraightBondContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：債券新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetStraightBondExchange']['address'])
        attribute = TestV1StraightBondContracts.bond_token_attribute(exchange_address)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        # 取扱トークンデータ挿入
        TestV1StraightBondContracts.list_token(session, bond_token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': bond_token['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
            'image_url': [
                {'type': 'small', 'url': ''},
                {'type': 'medium','url': ''},
                {'type': 'large','url': ''}
            ],
            'certification': []
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 発行済債券あり（2件）
    # cursor=設定なし、 limit=設定なし
    # -> 登録が新しい順にリストが返却
    def test_contracts_normal_2(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1StraightBondContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetStraightBondExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1StraightBondContracts.bond_token_attribute(exchange_address)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, bond_token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 1,
            'token_address': bond_list[1]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
                'type': 'small',
                'url': ''
            }, {
                'type': 'medium',
                'url': ''
            }, {
                'type': 'large',
                'url': ''
            }],
            'certification': []
        }, {
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
                'type': 'small',
                'url': ''
            }, {
                'type': 'medium',
                'url': ''
            }, {
                'type': 'large',
                'url': ''
            }],
            'certification': []
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    # 発行済債券あり（2件）
    # cursor=2、 limit=2
    # -> 登録が新しい順にリストが返却（2件）
    def test_contracts_normal_3(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1StraightBondContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetStraightBondExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1StraightBondContracts.bond_token_attribute(exchange_address)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, bond_token)

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 1,
            'token_address': bond_list[1]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
                'type': 'small',
                'url': ''
            }, {
                'type': 'medium',
                'url': ''
            }, {
                'type': 'large',
                'url': ''
            }],
            'certification': []
        }, {
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
                'type': 'small',
                'url': ''
            }, {
                'type': 'medium',
                'url': ''
            }, {
                'type': 'large',
                'url': ''
            }],
            'certification': []
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4＞
    # 発行済債券あり（2件）
    # cursor=1、 limit=1
    # -> 登録が新しい順にリストが返却（1件）
    def test_contracts_normal_4(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1StraightBondContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetStraightBondExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1StraightBondContracts.bond_token_attribute(exchange_address)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, bond_token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
                'type': 'small',
                'url': ''
            }, {
                'type': 'medium',
                'url': ''
            }, {
                'type': 'large',
                'url': ''
            }],
            'certification': []
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系5＞
    # 発行済債券あり（2件）
    # cursor=1、 limit=2
    # -> 登録が新しい順にリストが返却（1件）
    def test_contracts_normal_5(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1StraightBondContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：債券新規発行
        bond_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetStraightBondExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1StraightBondContracts.bond_token_attribute(exchange_address)
            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, bond_token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': bond_list[0]['address'],
            'token_template': 'IbetStraightBond',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
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
                'type': 'small',
                'url': ''
            }, {
                'type': 'medium',
                'url': ''
            }, {
                'type': 'large',
                'url': ''
            }],
            'certification': []
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_contracts_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v1/StraightBond/Contracts'
        }

    # ＜エラー系2-1＞
    # cursorに文字が含まれる
    # -> 入力エラー
    def test_contracts_error_2_1(self, client):
        query_string = 'cursor=a&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-2＞
    # cursorが負値
    # -> 入力エラー
    def test_contracts_error_2_2(self, client):
        query_string = 'cursor=-1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'cursor': 'min value is 0'}
        }

    # ＜エラー系2-3＞
    # cursorが小数
    # -> 入力エラー
    def test_contracts_error_2_3(self, client):
        query_string = 'cursor=0.1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-4＞
    # cursorがint最大値
    # -> 入力エラー
    def test_contracts_error_2_4(self, client):
        max_value = str(sys.maxsize)
        query_string = 'cursor=' + max_value + '&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'cursor parameter must be less than token list num'
        }

    # ＜エラー系3-1＞
    # limitに文字が含まれる
    # -> 入力エラー
    def test_contracts_error_3_1(self, client):
        query_string = 'cursor=1&limit=a'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系3-2＞
    # limitが負値
    # -> 入力エラー
    def test_contracts_error_3_2(self, client):
        query_string = 'cursor=1&limit=-1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'limit': 'min value is 0'}
        }

    # ＜エラー系3-3＞
    # limitが小数
    # -> 入力エラー
    def test_contracts_error_3_3(self, client):
        query_string = 'cursor=1&limit=0.1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

# [会員権]トークン一覧参照API
# /v1/Membership/Contracts
class TestV1MembershipContracts():

    # テスト対象API
    apiurl = '/v1/Membership/Contracts/'

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
            'transferable': True
        }
        return attribute

    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal.\
            unlockAccount(deployer['account_address'],deployer['password'])
        contract_address, abi = Contract.\
            deploy_contract('TokenList', [], deployer['account_address'])
        return {'address':contract_address, 'abi':abi}

    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.credit_card_availability = True
        listed_token.bank_payment_availability = True
        session.add(listed_token)

    # ＜正常系1＞
    # 発行済会員権あり（1件）
    # cursor=設定なし、 limit=設定なし
    # -> 1件返却
    def test_membershiplist_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1MembershipContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：会員権新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        attribute = TestV1MembershipContracts.token_attribute(exchange_address)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV1StraightBondContracts.list_token(session, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 0,
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
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 発行済会員権あり（2件）
    # cursor=設定なし、 limit=設定なし
    # -> 登録が新しい順にリストが返却
    def test_membershiplist_normal_2(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1MembershipContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：会員権新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1MembershipContracts.\
                token_attribute(exchange_address)
            token = membership_issue(issuer, attribute)
            membership_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 1,
                'token_address': issued_list[1]['address'],
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
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }, {
                'id': 0,
                'token_address': issued_list[0]['address'],
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
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    # 発行済会員権あり（2件）
    # cursor=2、 limit=2
    # -> 登録が新しい順にリストが返却（2件）
    def test_membershiplist_normal_3(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1MembershipContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：会員権新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1MembershipContracts.\
                token_attribute(exchange_address)
            token = membership_issue(issuer, attribute)
            membership_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 1,
                'token_address': issued_list[1]['address'],
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
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }, {
                'id': 0,
                'token_address': issued_list[0]['address'],
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
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4＞
    # 発行済会員権あり（2件）
    # cursor=1、 limit=1
    # -> 登録が新しい順にリストが返却（1件）
    def test_membershiplist_normal_4(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1MembershipContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：会員権新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1MembershipContracts.\
                token_attribute(exchange_address)
            token = membership_issue(issuer, attribute)
            membership_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': issued_list[0]['address'],
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
                {'type': 'small', 'url': ''},
                {'type': 'medium','url': ''},
                {'type': 'large','url': ''}
            ]
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系5＞
    # 発行済会員権あり（2件）
    # cursor=1、 limit=2
    # -> 登録が新しい順にリストが返却（1件）
    def test_membershiplist_normal_5(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1MembershipContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：会員権新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1MembershipContracts.\
                token_attribute(exchange_address)
            token = membership_issue(issuer, attribute)
            membership_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = 'cursor=1&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': issued_list[0]['address'],
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
                {'type': 'small', 'url': ''},
                {'type': 'medium','url': ''},
                {'type': 'large','url': ''}
            ]
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系6＞
    # 会員権発行（1件）　→　無効化
    # cursor=設定なし、 limit=設定なし
    # -> 0件返却
    def test_membershiplist_normal_6(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1MembershipContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：会員権新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetMembershipExchange']['address'])
        attribute = TestV1MembershipContracts.\
            token_attribute(exchange_address)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        # 取扱トークンデータ挿入
        TestV1StraightBondContracts.list_token(session, token)

        # Tokenの無効化
        membership_invalidate(issuer, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body


    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_membershiplist_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v1/Membership/Contracts'
        }

    # ＜エラー系2-1＞
    # cursorに文字が含まれる
    # -> 入力エラー
    def test_membershiplist_error_2_1(self, client):
        query_string = 'cursor=a&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-2＞
    # cursorが負値
    # -> 入力エラー
    def test_membershiplist_error_2_2(self, client):
        query_string = 'cursor=-1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'cursor': 'min value is 0'}
        }

    # ＜エラー系2-3＞
    # cursorが小数
    # -> 入力エラー
    def test_membershiplist_error_2_3(self, client):
        query_string = 'cursor=0.1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-4＞
    # cursorがint最大値
    # -> 入力エラー
    def test_membershiplist_error_2_4(self, client):
        max_value = str(sys.maxsize)
        query_string = 'cursor=' + max_value + '&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'cursor parameter must be less than token list num'
        }

    # ＜エラー系3-1＞
    # limitに文字が含まれる
    # -> 入力エラー
    def test_membershiplist_error_3_1(self, client):
        query_string = 'cursor=1&limit=a'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系3-2＞
    # limitが負値
    # -> 入力エラー
    def test_membershiplist_error_3_2(self, client):
        query_string = 'cursor=1&limit=-1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'limit': 'min value is 0'}
        }

    # ＜エラー系3-3＞
    # limitが小数
    # -> 入力エラー
    def test_membershiplist_error_3_3(self, client):
        query_string = 'cursor=1&limit=0.1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

# [クーポン]トークン一覧参照API
# /v1/Coupon/Contracts
class TestV1CouponContracts():

    # テスト対象API
    apiurl = '/v1/Coupon/Contracts/'

    def token_attribute(exchange_address):
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 10000,
            'tradableExchange': exchange_address,
            'details': 'クーポン詳細',
            'memo': 'クーポンメモ欄',
            'expirationDate': '20191231',
            'transferable': True
        }
        return attribute

    def tokenlist_contract():
        deployer = eth_account['deployer']
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal.\
            unlockAccount(deployer['account_address'],deployer['password'])
        contract_address, abi = Contract.\
            deploy_contract('TokenList', [], deployer['account_address'])
        return {'address':contract_address, 'abi':abi}

    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.credit_card_availability = True
        listed_token.bank_payment_availability = True
        session.add(listed_token)

    # ＜正常系1＞
    # 発行済クーポンあり（1件）
    # cursor=設定なし、 limit=設定なし
    # -> 1件返却
    def test_couponlist_normal_1(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1CouponContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV1CouponContracts.token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV1StraightBondContracts.list_token(session, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 0,
                'token_address': token['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
                'is_valid': True,
                'initial_offering_status': False,
                'image_url': [
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系2＞
    # 発行済クーポンあり（2件）
    # cursor=設定なし、 limit=設定なし
    # -> 登録が新しい順にリストが返却
    def test_couponlist_normal_2(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1CouponContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1CouponContracts.\
                token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 1,
                'token_address': issued_list[1]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
                'is_valid': True,
                'initial_offering_status': False,
                'image_url': [
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }, {
                'id': 0,
                'token_address': issued_list[0]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
                'is_valid': True,
                'initial_offering_status': False,
                'image_url': [
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系3＞
    # 発行済クーポンあり（2件）
    # cursor=2、 limit=2
    # -> 登録が新しい順にリストが返却（2件）
    def test_couponlist_normal_3(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1CouponContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1CouponContracts.\
                token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [
            {
                'id': 1,
                'token_address': issued_list[1]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
                'is_valid': True,
                'initial_offering_status': False,
                'image_url': [
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }, {
                'id': 0,
                'token_address': issued_list[0]['address'],
                'token_template': 'IbetCoupon',
                'owner_address': issuer['account_address'],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 10000,
                'details': 'クーポン詳細',
                'memo': 'クーポンメモ欄',
                'expiration_date': '20191231',
                'transferable': True,
                'is_valid': True,
                'initial_offering_status': False,
                'image_url': [
                    {'type': 'small', 'url': ''},
                    {'type': 'medium','url': ''},
                    {'type': 'large','url': ''}
                ]
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系4＞
    # 発行済クーポンあり（2件）
    # cursor=1、 limit=1
    # -> 登録が新しい順にリストが返却（1件）
    def test_couponlist_normal_4(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1CouponContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1CouponContracts.\
                token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': issued_list[0]['address'],
            'token_template': 'IbetCoupon',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'total_supply': 10000,
            'details': 'クーポン詳細',
            'memo': 'クーポンメモ欄',
            'expiration_date': '20191231',
            'transferable': True,
            'is_valid': True,
            'initial_offering_status': False,
            'image_url': [
                {'type': 'small', 'url': ''},
                {'type': 'medium','url': ''},
                {'type': 'large','url': ''}
            ]
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系5＞
    # 発行済クーポンあり（2件）
    # cursor=1、 limit=2
    # -> 登録が新しい順にリストが返却（1件）
    def test_couponlist_normal_5(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1CouponContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：新規発行
        issued_list = []
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestV1CouponContracts.\
                token_attribute(exchange_address)
            token = issue_coupon_token(issuer, attribute)
            coupon_register_list(issuer, token, token_list)
            issued_list.append(token)
            # 取扱トークンデータ挿入
            TestV1StraightBondContracts.list_token(session, token)

        query_string = 'cursor=1&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id': 0,
            'token_address': issued_list[0]['address'],
            'token_template': 'IbetCoupon',
            'owner_address': issuer['account_address'],
            'company_name': '',
            'rsa_publickey': '',
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'total_supply': 10000,
            'details': 'クーポン詳細',
            'memo': 'クーポンメモ欄',
            'expiration_date': '20191231',
            'transferable': True,
            'is_valid': True,
            'initial_offering_status': False,
            'image_url': [
                {'type': 'small', 'url': ''},
                {'type': 'medium','url': ''},
                {'type': 'large','url': ''}
            ]
        }]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # ＜正常系6＞
    # クーポン発行（1件）　→　無効化
    # cursor=設定なし、 limit=設定なし
    # -> 0件返却
    def test_couponlist_normal_6(self, client, session, shared_contract):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1CouponContracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：新規発行
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        attribute = TestV1CouponContracts.\
            token_attribute(exchange_address)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # 取扱トークンデータ挿入
        TestV1StraightBondContracts.list_token(session, token)

        # Tokenの無効化
        invalidate_coupon_token(issuer, token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body


    # ＜エラー系1＞
    # HTTPメソッド不正
    # -> 404エラー
    def test_couponlist_error_1(self, client):
        headers = {'Content-Type': 'application/json'}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 404
        assert resp.json['meta'] == {
            'code': 10,
            'message': 'Not Supported',
            'description': 'method: POST, url: /v1/Coupon/Contracts'
        }

    # ＜エラー系2-1＞
    # cursorに文字が含まれる
    # -> 入力エラー
    def test_couponlist_error_2_1(self, client):
        query_string = 'cursor=a&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-2＞
    # cursorが負値
    # -> 入力エラー
    def test_couponlist_error_2_2(self, client):
        query_string = 'cursor=-1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'cursor': 'min value is 0'}
        }

    # ＜エラー系2-3＞
    # cursorが小数
    # -> 入力エラー
    def test_couponlist_error_2_3(self, client):
        query_string = 'cursor=0.1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'cursor': [
                    "field 'cursor' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系2-4＞
    # cursorがint最大値
    # -> 入力エラー
    def test_couponlist_error_2_4(self, client):
        max_value = str(sys.maxsize)
        query_string = 'cursor=' + max_value + '&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': 'cursor parameter must be less than token list num'
        }

    # ＜エラー系3-1＞
    # limitに文字が含まれる
    # -> 入力エラー
    def test_couponlist_error_3_1(self, client):
        query_string = 'cursor=1&limit=a'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }

    # ＜エラー系3-2＞
    # limitが負値
    # -> 入力エラー
    def test_couponlist_error_3_2(self, client):
        query_string = 'cursor=1&limit=-1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {'limit': 'min value is 0'}
        }

    # ＜エラー系3-3＞
    # limitが小数
    # -> 入力エラー
    def test_couponlist_error_3_3(self, client):
        query_string = 'cursor=1&limit=0.1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': 'Invalid Parameter',
            'description': {
                'limit': [
                    "field 'limit' could not be coerced",
                    'must be of integer type'
                ]
            }
        }
