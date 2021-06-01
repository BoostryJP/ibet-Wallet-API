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
import datetime
import os
import sys
import pytest
import re

from sqlalchemy import desc
from web3 import Web3
from web3.middleware import geth_poa_middleware

path = os.path.join(os.path.dirname(__file__), "../../")
sys.path.append(path)
from app import config
from app.model.notification import Notification, NotificationType
from app.model.listing import Listing
from app.tests.contract_modules import (
    issue_bond_token,
    offer_bond_token,
    register_personalinfo,
    register_payment_gateway,
    register_bond_list,
)
from batch.tests.conftest import eth_account


web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


@pytest.fixture(scope="function")
def watcher_transfer(shared_contract):
    token_list = shared_contract['TokenList']
    config.TOKEN_LIST_CONTRACT_ADDRESS = token_list['address']
    from batch.processor_Notifications_Bond_Token import WatchTransfer
    return WatchTransfer()


class TestProcessorNotificationsBondTokenWatchTransfer:
    """
    Test Case for WatchStartInitialOffering()
    """
    @staticmethod
    def list_token(token_address, session):
        listed_token = Listing()
        listed_token.token_address = token_address
        listed_token.is_public = True
        listed_token.max_holding_quantity = 1
        listed_token.max_sell_amount = 1000
        session.add(listed_token)
        session.commit()

    @staticmethod
    def bond_transfer(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account['issuer']
        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 債券トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) 募集
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
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)
        return bond_token

    @staticmethod
    def bond_transfer_without_register(bond_exchange, personal_info):
        issuer = eth_account['issuer']
        # ＜発行体オペレーション＞
        #   1) 債券トークン発行
        #   2) 募集
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
        bond_token = issue_bond_token(issuer, attribute)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)
        return bond_token

    ####################################################################
    # Normal
    ####################################################################
    # Normal_1
    # is_registered : True
    def test_normal_1(self, watcher_transfer, shared_contract, session):

        started_timestamp = datetime.datetime.utcnow().replace(microsecond=0)

        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']
        payment_gateway = shared_contract['PaymentGateway']
        token_list = shared_contract['TokenList']

        bond_token = self.bond_transfer(bond_exchange, personal_info, payment_gateway, token_list)
        self.list_token(bond_token['address'], session)
        # テスト実行
        watcher_transfer.loop()

        # Assertion
        expected_metadata = {
            "company_name": '',
            "token_address": bond_token['address'],
            "token_name": "テスト債券",
            "exchange_address": "",
            "token_type": "IbetStraightBond"
        }

        expected_args = {
            "from": eth_account['issuer']['account_address'],
            "to": bond_exchange['address'],
            "value": 1000000
        }

        notification = session.query(Notification). \
            filter(Notification.notification_type == NotificationType.TRANSFER.value). \
            filter(Notification.metainfo['token_address'].as_string() == bond_token['address']). \
            first()
        # blockNumber: 12桁、transactionIndex: 6桁、logIndex: 6桁、option_type=0:2桁
        assert re.search('0x[0-9a-fA-F]{12}0{6}0{6}0{2}', notification.notification_id) is not None
        assert notification.priority == 0
        assert notification.address == bond_exchange['address']
        assert notification.is_read is False
        assert notification.is_flagged is False
        assert notification.is_deleted is False
        assert notification.deleted_at is None
        assert notification.block_timestamp >= started_timestamp
        assert notification.block_timestamp <= (datetime.datetime.utcnow() + datetime.timedelta(seconds=10))
        assert notification.args == expected_args
        assert notification.metainfo == expected_metadata

    # Normal_2
    # is_registered : False
    def test_normal_2(self, watcher_transfer, shared_contract, session):

        bond_exchange = shared_contract['IbetStraightBondExchange']
        personal_info = shared_contract['PersonalInfo']

        bond_token = self.bond_transfer_without_register(bond_exchange, personal_info)
        self.list_token(bond_token['address'], session)
        # テスト実行
        watcher_transfer.loop()

        notification = session.query(Notification). \
            filter(Notification.notification_type == NotificationType.TRANSFER.value). \
            filter(Notification.metainfo['token_address'].as_string() == bond_token['address']). \
            first()
        # blockNumber: 12桁、transactionIndex: 6桁、logIndex: 6桁、option_type=0:2桁
        assert notification is None

    # Normal_3 : No Listing Data
    def test_normal_3(self, watcher_transfer, session):
        # テスト実行
        watcher_transfer.loop()
        notification = session.query(Notification).first()
        assert notification is None
