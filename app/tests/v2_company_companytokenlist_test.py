"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.model import Listing
from .contract_modules import (
    issue_bond_token,
    register_bond_list,
    issue_share_token,
    register_share_list,
    membership_issue,
    membership_register_list,
    issue_coupon_token,
    coupon_register_list
)
from .account_config import eth_account

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)

"""
発行会社トークン一覧参照API
/v2/Company/{eth_address}/Tokens
"""


class TestV2CompanyCompanyTokenList:
    # テスト対象API
    apiurl = '/v2/Company/{eth_address}/Tokens'

    @staticmethod
    def _bond_attribute(exchange_address, personal_info_address):
        attribute = {
            'name': 'テスト債券',
            'symbol': 'BOND',
            'totalSupply': 1000000,
            'tradableExchange': exchange_address,
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
            'personalInfoAddress': personal_info_address
        }
        return attribute

    @staticmethod
    def _share_attribute(exchange_address, personal_info_address):
        attribute = {
            'name': 'テスト株式',
            'symbol': 'SHARE',
            'tradableExchange': exchange_address,
            'personalInfoAddress': personal_info_address,
            'totalSupply': 1000000,
            'issuePrice': 10000,
            'principalValue': 10000,
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
    def _membership_attribute(exchange_address):
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
    def _coupon_attribute(exchange_address):
        attribute = {
            'name': 'テストクーポン',
            'symbol': 'COUPON',
            'totalSupply': 1000000,
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
    def _insert_listing(session, token_address, owner_address):
        listing = Listing()
        listing.token_address = token_address
        listing.is_public = True
        listing.owner_address = owner_address
        session.add(listing)

    @staticmethod
    def _set_env(shared_contract):
        bond_exchange = shared_contract['IbetStraightBondExchange']
        membership_exchange = shared_contract['IbetMembershipExchange']
        coupon_exchange = shared_contract['IbetCouponExchange']
        share_exchange = shared_contract["IbetShareExchange"]
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange['address']
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange['address']
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange['address']
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
        return bond_exchange, membership_exchange, coupon_exchange, share_exchange, personal_info, payment_gateway, token_list

    ###########################################################################
    # Normal
    ###########################################################################

    # Normal_1
    # 債券トークン
    def test_normal_1(self, client, session, shared_contract):
        # 環境変数設定変更
        config.BOND_TOKEN_ENABLED = True
        bond_exchange, _, _, _, personal_info, _, token_list = self._set_env(shared_contract)

        # 新規トークン発行
        issuer = eth_account['issuer']
        attribute = self._bond_attribute(bond_exchange["address"], personal_info["address"])
        token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, token, token_list)
        self._insert_listing(session, token["address"], issuer["account_address"])

        url = self.apiurl.replace("{eth_address}", issuer["account_address"])
        resp = client.simulate_get(url)

        assumed_body = [
            {
                'token_address': token["address"],
                'token_template': 'IbetStraightBond',
                'owner_address': issuer["account_address"],
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
                'isRedeemed': False,
                'transferable': True,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'certification': [],
                'initial_offering_status': False,
                'max_holding_quantity': None,
                'max_sell_amount': None,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_2
    # 株式トークン
    def test_normal_2(self, client, session, shared_contract):
        # 環境変数設定変更
        config.SHARE_TOKEN_ENABLED = True
        _, _, _, share_exchange, personal_info, _, token_list = self._set_env(shared_contract)

        # 新規トークン発行
        issuer = eth_account['issuer']
        attribute = self._share_attribute(share_exchange["address"], personal_info["address"])
        token = issue_share_token(issuer, attribute)
        register_share_list(issuer, token, token_list)
        self._insert_listing(session, token["address"], issuer["account_address"])

        url = self.apiurl.replace("{eth_address}", issuer["account_address"])
        resp = client.simulate_get(url)

        assumed_body = [
            {
                'token_address': token["address"],
                'token_template': 'IbetShare',
                'owner_address': issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テスト株式',
                'symbol': 'SHARE',
                'total_supply': 1000000,
                'issue_price': 10000,
                'principal_value': 10000,
                'dividend_information': {
                    'dividends': 1.01,
                    'dividend_record_date': '20200909',
                    'dividend_payment_date': '20201001'
                },
                'cancellation_date': '20210101',
                'reference_urls': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'image_url': [],
                'memo': 'メモ',
                'transferable': True,
                'offering_status': False,
                'status': True,
                'transfer_approval_required': False,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー',
                'max_holding_quantity': None,
                'max_sell_amount': None,
                'is_canceled': False
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_3
    # 会員権トークン
    def test_normal_3(self, client, session, shared_contract):
        # 環境変数設定変更
        config.MEMBERSHIP_TOKEN_ENABLED = True
        _, membership_exchange, _, _, _, _, token_list = self._set_env(shared_contract)

        # 新規トークン発行
        issuer = eth_account['issuer']
        attribute = self._membership_attribute(membership_exchange["address"])
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        self._insert_listing(session, token["address"], issuer["account_address"])

        url = self.apiurl.replace("{eth_address}", issuer["account_address"])
        resp = client.simulate_get(url)

        assumed_body = [
            {
                'token_address': token["address"],
                'token_template': 'IbetMembership',
                'owner_address': issuer["account_address"],
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
                'max_holding_quantity': None,
                'max_sell_amount': None,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_4
    # クーポントークン
    def test_normal_4(self, client, session, shared_contract):
        # 環境変数設定変更
        config.COUPON_TOKEN_ENABLED = True
        _, _, coupon_exchange, _, _, _, token_list = self._set_env(shared_contract)

        # 新規トークン発行
        issuer = eth_account['issuer']
        attribute = self._coupon_attribute(coupon_exchange["address"])
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        self._insert_listing(session, token["address"], issuer["account_address"])

        url = self.apiurl.replace("{eth_address}", issuer["account_address"])
        resp = client.simulate_get(url)

        assumed_body = [
            {
                'token_address': token["address"],
                'token_template': 'IbetCoupon',
                'owner_address': issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'クーポンメモ欄',
                'transferable': True,
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': None,
                'max_sell_amount': None,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_5
    # 複数種類のトークン
    def test_normal_5(self, client, session, shared_contract):
        issuer = eth_account['issuer']

        # 環境変数設定変更
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        _, membership_exchange, coupon_exchange, _, _, _, token_list = self._set_env(shared_contract)

        # 新規トークン発行（会員権）
        attribute = self._membership_attribute(membership_exchange["address"])
        membership_token = membership_issue(issuer, attribute)
        membership_register_list(issuer, membership_token, token_list)
        self._insert_listing(session, membership_token["address"], issuer["account_address"])

        # 新規トークン発行（クーポン）
        attribute = self._coupon_attribute(coupon_exchange["address"])
        coupon_token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, coupon_token, token_list)
        self._insert_listing(session, coupon_token["address"], issuer["account_address"])

        url = self.apiurl.replace("{eth_address}", issuer["account_address"])
        resp = client.simulate_get(url)

        assumed_body = [
            {
                'token_address': coupon_token["address"],
                'token_template': 'IbetCoupon',
                'owner_address': issuer["account_address"],
                'company_name': '',
                'rsa_publickey': '',
                'name': 'テストクーポン',
                'symbol': 'COUPON',
                'total_supply': 1000000,
                'details': 'クーポン詳細',
                'return_details': 'リターン詳細',
                'expiration_date': '20191231',
                'memo': 'クーポンメモ欄',
                'transferable': True,
                'status': True,
                'initial_offering_status': False,
                'image_url': [
                    {'id': 1, 'url': ''},
                    {'id': 2, 'url': ''},
                    {'id': 3, 'url': ''}
                ],
                'max_holding_quantity': None,
                'max_sell_amount': None,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            },
            {
                'token_address': membership_token["address"],
                'token_template': 'IbetMembership',
                'owner_address': issuer["account_address"],
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
                'max_holding_quantity': None,
                'max_sell_amount': None,
                'contact_information': '問い合わせ先',
                'privacy_policy': 'プライバシーポリシー'
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # Normal_6
    # データ0件
    def test_normal_6(self, client, session):
        issuer = eth_account['issuer']

        url = self.apiurl.replace("{eth_address}", issuer["account_address"])
        resp = client.simulate_get(url)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    ###########################################################################
    # Error
    ###########################################################################

    # エラー系：入力値エラー（eth_addressがアドレスフォーマットではない）
    def test_error_1(self, client):
        eth_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い

        url = self.apiurl.replace("{eth_address}", eth_address)
        resp = client.simulate_get(url)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': "Invalid Parameter",
            "description": "invalid eth_address"
        }
