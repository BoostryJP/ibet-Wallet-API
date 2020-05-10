# -*- coding: utf-8 -*-
from datetime import datetime

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.model import Listing, PrivateListing

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

"""
発行会社トークン一覧参照API
/v2/Companiy/{eth_address}/Tokens
"""


class TestV2CompanyCompanyTokenList:
    # テスト対象API
    apiurl = '/v2/Company/{eth_address}/Tokens'

    def _insert_test_data(self, session):
        listing1 = Listing()
        listing1.created = datetime(2020, 2, 28, 23, 59, 59, 999999)
        listing1.modified = datetime(2020, 2, 28, 23, 59, 59, 999999)
        listing1.id = 1
        listing1.token_address = "0xe44d4EC8cEF193cD8ef96912A8c93e4aa255AFA4"
        listing1.max_holding_quantity = 10000000
        listing1.max_sell_amount = 1000000
        listing1.payment_method_credit_card = True
        listing1.payment_method_bank = True
        listing1.owner_address = "0x865DE50Bb0F21C3f318B736c04D2b6fF7DeA3BFD"

        listing2 = Listing()
        listing2.created = datetime(2020, 2, 28, 23, 59, 59, 0)
        listing2.modified = datetime(2020, 2, 28, 23, 59, 59, 0)
        listing2.id = 2
        listing2.token_address = "0x92057E290D1232530e8A4ff4599cAa818d9b8B34"
        listing2.max_holding_quantity = 10000
        listing2.max_sell_amount = 1000
        listing2.payment_method_credit_card = False
        listing2.payment_method_bank = True
        listing2.owner_address = "0xXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

        private_listing1 = PrivateListing()
        private_listing1.created = datetime(2020, 2, 29, 0, 0, 0, 1)
        private_listing1.modified = datetime(2020, 2, 29, 0, 0, 0, 1)
        private_listing1.id = 1
        private_listing1.token_address = "0x1D70136cf3282a28D0d2369E55BA1f893b0efb28"
        private_listing1.max_holding_quantity = 10000000
        private_listing1.max_sell_amount = 1000000
        private_listing1.payment_method_credit_card = True
        private_listing1.payment_method_bank = True
        private_listing1.owner_address = "0x865DE50Bb0F21C3f318B736c04D2b6fF7DeA3BFD"

        private_listing2 = PrivateListing()
        private_listing2.created = datetime(2020, 2, 29, 0, 0, 0, 1)
        private_listing2.modified = datetime(2020, 2, 29, 0, 0, 0, 1)
        private_listing2.id = 2
        private_listing2.token_address = "0xYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"
        private_listing2.max_holding_quantity = 10000
        private_listing2.max_sell_amount = 1000
        private_listing2.payment_method_credit_card = False
        private_listing2.payment_method_bank = True
        private_listing2.owner_address = "0xYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY"

        session.bulk_save_objects([listing1, listing2, private_listing1, private_listing2])

    # 正常系1-1： 会社が発行しているトークンアドレスが返却される
    def test_normal_1_1(self, client, session):
        self._insert_test_data(session)

        url = self.apiurl.replace("{eth_address}", "0x865DE50Bb0F21C3f318B736c04D2b6fF7DeA3BFD")
        resp = client.simulate_get(url)

        assumed_body = {
            'token_list': [
                '0x1D70136cf3282a28D0d2369E55BA1f893b0efb28',
                '0xe44d4EC8cEF193cD8ef96912A8c93e4aa255AFA4',
            ]
        }

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert resp.json['data']['token_list']
        for x, y in zip(resp.json['data']['token_list'], assumed_body['token_list']):
            assert x == y

    # 正常系1-2： 0件リターン
    def test_normal_1_2(self, client, session):
        self._insert_test_data(session)

        url = self.apiurl.replace("{eth_address}", "0x9ba26793217B1780Ee2cF3cAfEb8e0DB10Dda4De")
        resp = client.simulate_get(url)

        assumed_body = [
            {
                'token_list': []
            },
        ]

        assert resp.status_code == 200
        assert resp.json['meta'] == {'code': 200, 'message': 'OK'}
        assert len(resp.json['data']['token_list']) == 0

    # エラー系：入力値エラー（eth_addressがアドレスフォーマットではない）
    def test_membership_tick_error_3(self, client, session):
        self._insert_test_data(session)

        eth_address = "0xe883a6f441ad5682d37df31d34fc012bcb07a74"  # アドレス長が短い
        # request_params = {"address_list": [token_address]}

        url = self.apiurl.replace("{eth_address}", eth_address)
        resp = client.simulate_get(url)

        assert resp.status_code == 400
        assert resp.json['meta'] == {
            'code': 88,
            'message': "Invalid Parameter",
            "description": "invalid eth_address"
        }