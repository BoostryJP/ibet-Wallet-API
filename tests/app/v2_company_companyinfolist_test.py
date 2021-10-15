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
from eth_utils import to_checksum_address
from web3 import Web3
from web3.middleware import geth_poa_middleware

from app.model.db import Listing
from app import config
from app.contracts import Contract
from tests.account_config import eth_account
from tests.contract_modules import (
    issue_coupon_token,
    coupon_register_list
)

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestCompanyCompanyInfoList:
    # テスト対象API
    apiurl = '/v2/Companies'

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
        contract_address, abi = Contract. \
            deploy_contract('TokenList', [], deployer['account_address'])
        return {'address': contract_address, 'abi': abi}

    @staticmethod
    def list_token(session, token):
        listed_token = Listing()
        listed_token.token_address = token['address']
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)

    # 正常系1-1： 登録済みのトークンアドレスに紐づく会社情報が返却される
    def test_normal_1_1(self, client, session, shared_contract, mocked_company_list):
        # テスト用アカウント
        issuerList = [eth_account['issuer'], eth_account['deployer']]

        # TokenListコントラクトアドレスの設定
        token_list = TestCompanyCompanyInfoList.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行（クーポン）
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestCompanyCompanyInfoList. \
                token_attribute(exchange_address)
            token = issue_coupon_token(issuerList[i], attribute)
            coupon_register_list(issuerList[i], token, token_list)
            # 取扱トークンデータ挿入
            TestCompanyCompanyInfoList.list_token(session, token)

        resp = client.simulate_get(self.apiurl)

        assumed_body = [
            {
                "address": eth_account['issuer']['account_address'],
                "corporate_name": "株式会社DEMO",
                "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
                "homepage": "https://www.aaaa.com/jp/"
            },
            {
                "address": eth_account['deployer']['account_address'],
                "corporate_name": "株式会社DEMO",
                "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
                "homepage": "https://www.aaaa.com/jp/"
            }
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body

    # 正常系1-2： listing対象とcompanylistが突合されず0件リターン
    def test_normal_1_2(self, client, shared_contract, mocked_company_list, session):
        # テスト用アカウント
        issuerList = [eth_account['issuer'], eth_account['deployer']]

        # TokenListコントラクトアドレスの設定
        token_list = TestCompanyCompanyInfoList.tokenlist_contract()
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']

        # データ準備：新規発行（クーポン）
        exchange_address = \
            to_checksum_address(
                shared_contract['IbetCouponExchange']['address'])
        for i in range(0, 2):
            attribute = TestCompanyCompanyInfoList. \
                token_attribute(exchange_address)
            token = issue_coupon_token(issuerList[i], attribute)
            coupon_register_list(issuerList[i], token, token_list)

        resp = client.simulate_get(self.apiurl)

        assumed_body = []

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data'] == assumed_body
