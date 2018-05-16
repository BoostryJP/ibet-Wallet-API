# -*- coding: utf-8 -*-
import json
import os
import time

from eth_utils import to_checksum_address
from web3 import Web3

import app.model
from app.model import TokenTemplate
from app import config

from .account_config import eth_account
from .contract_config import IbetStraightBond, TokenList
from .contract_modules import issue_bond_token, register_bond_list


# トークン一覧参照API
# /v1/Contracts
class TestV1Contracts():

    # テスト対象API
    apiurl = '/v1/Contracts/'

    def tokenlist_contract():
        deployer = eth_account['deployer']

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        web3.eth.defaultAccount = deployer['account_address']
        web3.personal.unlockAccount(deployer['account_address'],deployer['password'])
        TokenListContract = web3.eth.contract(
            abi = TokenList['abi'],
            bytecode = TokenList['bytecode'],
            bytecode_runtime = TokenList['bytecode_runtime'],
        )

        tx_hash = TokenListContract.deploy(
            transaction={'from':deployer['account_address'], 'gas':4000000}
        ).hex()

        count = 0
        tx = None
        while True:
            time.sleep(1)
            try:
                tx = web3.eth.getTransactionReceipt(tx_hash)
            except:
                continue
            count += 1
            if tx is not None or count > 10:
                break

        contract_address = ''
        if tx is not None :
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
            if 'contractAddress' in tx.keys():
                contract_address = tx['contractAddress']

        return {'address':contract_address, 'abi':TokenList['abi']}

    # ＜正常系1＞
    # 発行済債券あり（1件）
    # cursor=設定なし、 limit=設定なし
    # -> 1件返却
    def test_contracts_normal_1(self, client, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1Contracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：TokenTemplate登録
        tokenTemplate = TokenTemplate()
        tokenTemplate.id = 1
        tokenTemplate.template_name = 'IbetStraightBond'
        tokenTemplate.abi = IbetStraightBond['abi']
        session.add(tokenTemplate)

        # データ準備：債券新規発行
        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'faceValue': 10000,
            'interestRate': 1000,
            'interestPaymentDate1': '0331',
            'interestPaymentDate2': '0930',
            'redemptionDate': '20191231',
            'redemptionAmount': 10000,
            'returnDate': '20191231',
            'returnAmount': '商品券をプレゼント',
            'purpose': '新商品の開発資金として利用。'
        }

        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id':
            0,
            'token_address':
            bond_token['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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

    # ＜正常系2＞
    # 発行済債券あり（2件）
    # cursor=設定なし、 limit=設定なし
    # -> 登録が新しい順にリストが返却
    def test_contracts_normal_2(self, client, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1Contracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：TokenTemplate登録
        tokenTemplate = TokenTemplate()
        tokenTemplate.id = 1
        tokenTemplate.template_name = 'IbetStraightBond'
        tokenTemplate.abi = IbetStraightBond['abi']
        session.add(tokenTemplate)

        # データ準備：債券新規発行
        bond_list = []
        for i in range(0, 2):
            attribute = {
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
                'faceValue': 10000,
                'interestRate': 1000,
                'interestPaymentDate1': '0331',
                'interestPaymentDate2': '0930',
                'redemptionDate': '20191231',
                'redemptionAmount': 10000,
                'returnDate': '20191231',
                'returnAmount': '商品券をプレゼント',
                'purpose': '新商品の開発資金として利用。'
            }

            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)

        query_string = ''
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id':
            1,
            'token_address':
            bond_list[1]['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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
            'id':
            0,
            'token_address':
            bond_list[0]['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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
    def test_contracts_normal_3(self, client, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1Contracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：TokenTemplate登録
        tokenTemplate = TokenTemplate()
        tokenTemplate.id = 1
        tokenTemplate.template_name = 'IbetStraightBond'
        tokenTemplate.abi = IbetStraightBond['abi']
        session.add(tokenTemplate)

        # データ準備：債券新規発行
        bond_list = []
        for i in range(0, 2):
            attribute = {
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
                'faceValue': 10000,
                'interestRate': 1000,
                'interestPaymentDate1': '0331',
                'interestPaymentDate2': '0930',
                'redemptionDate': '20191231',
                'redemptionAmount': 10000,
                'returnDate': '20191231',
                'returnAmount': '商品券をプレゼント',
                'purpose': '新商品の開発資金として利用。'
            }

            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)

        query_string = 'cursor=2&limit=2'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id':
            1,
            'token_address':
            bond_list[1]['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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
            'id':
            0,
            'token_address':
            bond_list[0]['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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
    def test_contracts_normal_4(self, client, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1Contracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：TokenTemplate登録
        tokenTemplate = TokenTemplate()
        tokenTemplate.id = 1
        tokenTemplate.template_name = 'IbetStraightBond'
        tokenTemplate.abi = IbetStraightBond['abi']
        session.add(tokenTemplate)

        # データ準備：債券新規発行
        bond_list = []
        for i in range(0, 2):
            attribute = {
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
                'faceValue': 10000,
                'interestRate': 1000,
                'interestPaymentDate1': '0331',
                'interestPaymentDate2': '0930',
                'redemptionDate': '20191231',
                'redemptionAmount': 10000,
                'returnDate': '20191231',
                'returnAmount': '商品券をプレゼント',
                'purpose': '新商品の開発資金として利用。'
            }

            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id':
            0,
            'token_address':
            bond_list[0]['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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
    def test_contracts_normal_5(self, client, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1Contracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：TokenTemplate登録
        tokenTemplate = TokenTemplate()
        tokenTemplate.id = 1
        tokenTemplate.template_name = 'IbetStraightBond'
        tokenTemplate.abi = IbetStraightBond['abi']
        session.add(tokenTemplate)

        # データ準備：債券新規発行
        bond_list = []
        for i in range(0, 2):
            attribute = {
                'name': 'テスト債券',
                'symbol': 'BOND',
                'totalSupply': 1000000,
                'faceValue': 10000,
                'interestRate': 1000,
                'interestPaymentDate1': '0331',
                'interestPaymentDate2': '0930',
                'redemptionDate': '20191231',
                'redemptionAmount': 10000,
                'returnDate': '20191231',
                'returnAmount': '商品券をプレゼント',
                'purpose': '新商品の開発資金として利用。'
            }

            bond_token = issue_bond_token(issuer, attribute)
            register_bond_list(issuer, bond_token, token_list)
            bond_list.append(bond_token)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = [{
            'id':
            0,
            'token_address':
            bond_list[0]['address'],
            'token_template':
            'IbetStraightBond',
            'owner_address':
            issuer['account_address'],
            'company_name':
            '',
            'rsa_publickey':
            '',
            'name':
            'テスト債券',
            'symbol':
            'BOND',
            'totalSupply':
            1000000,
            'faceValue':
            10000,
            'interestRate':
            1000,
            'interestPaymentDate1':
            '0331',
            'interestPaymentDate2':
            '0930',
            'redemptionDate':
            '20191231',
            'redemptionAmount':
            10000,
            'returnDate':
            '20191231',
            'returnAmount':
            '商品券をプレゼント',
            'purpose':
            '新商品の開発資金として利用。',
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

    # ＜正常系6＞
    # 債券未発行、商品リスト（TokenList）のみ登録あり
    # -> ゼロ件リストが返却
    def test_contracts_normal_6(self, client, session):
        # テスト用アカウント
        issuer = eth_account['issuer']

        # TokenListコントラクト
        token_list = TestV1Contracts.tokenlist_contract()
        os.environ["TOKEN_LIST_CONTRACT_ADDRESS"] = token_list['address']

        # データ準備：TokenTemplate登録
        tokenTemplate = TokenTemplate()
        tokenTemplate.id = 1
        tokenTemplate.template_name = 'IbetStraightBond'
        tokenTemplate.abi = IbetStraightBond['abi']
        session.add(tokenTemplate)

        # データ準備：商品リスト登録
        token_address = to_checksum_address(
            '0xe883a6f441ad5682d37df31d34fc012bcb07a740')  # 任意のアドレス
        bond_token = {'address': token_address, 'abi': ''}
        register_bond_list(issuer, bond_token, token_list)

        query_string = 'cursor=1&limit=1'
        resp = client.simulate_get(self.apiurl, query_string=query_string)

        assumed_body = []

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
            'description': 'method: POST, url: /v1/Contracts'
        }

    # ＜エラー系2＞
    # cursorに文字が含まれる
    # -> 入力エラー
    def test_contracts_error_2(self, client):
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

    # ＜エラー系3＞
    # limitに文字が含まれる
    # -> 入力エラー
    def test_contracts_error_3(self, client):
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
