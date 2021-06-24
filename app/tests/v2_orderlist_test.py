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
from app.model import (
    IDXOrder as Order,
    IDXAgreement as Agreement,
    AgreementStatus
)

from app.tests.contract_modules import *

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


class TestV2OrderList:
    """
    Test Case for v2.order_list.OrderList
    """

    # Test target API
    base_url = "/v2/OrderList/"

    @staticmethod
    def bond_token_attribute(exchange, personal_info):
        attribute = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange["address"],
            "faceValue": 10000,
            "interestRate": 602,
            "interestPaymentDate1": "0101",
            "interestPaymentDate2": "0201",
            "interestPaymentDate3": "0301",
            "interestPaymentDate4": "0401",
            "interestPaymentDate5": "0501",
            "interestPaymentDate6": "0601",
            "interestPaymentDate7": "0701",
            "interestPaymentDate8": "0801",
            "interestPaymentDate9": "0901",
            "interestPaymentDate10": "1001",
            "interestPaymentDate11": "1101",
            "interestPaymentDate12": "1201",
            "redemptionDate": "20191231",
            "redemptionValue": 10000,
            "returnDate": "20191231",
            "returnAmount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "memo": "メモ",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "personalInfoAddress": personal_info["address"]
        }
        return attribute

    # Emit order event
    # from issuer account
    @staticmethod
    def bond_order_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        attribute = TestV2OrderList.bond_token_attribute(bond_exchange, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)
        order_id = get_latest_orderid(bond_exchange)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # Emit agreement event
    # from trader account
    @staticmethod
    def bond_agreement_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestV2OrderList.bond_token_attribute(bond_exchange, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        order_id = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, order_id, 100)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # Emit settlement event
    # from trader account
    @staticmethod
    def bond_settlement_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestV2OrderList.bond_token_attribute(bond_exchange, personal_info)

        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        order_id = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, order_id, 100)

        agreement_id = get_latest_agreementid(bond_exchange, order_id)
        bond_confirm_agreement(agent, bond_exchange, order_id, agreement_id)

        return bond_token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract["IbetStraightBondExchange"]
        membership_exchange = shared_contract["IbetMembershipExchange"]
        coupon_exchange = shared_contract["IbetCouponExchange"]
        personal_info = shared_contract["PersonalInfo"]
        payment_gateway = shared_contract["PaymentGateway"]
        token_list = shared_contract["TokenList"]
        config.BOND_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange["address"]
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, personal_info, payment_gateway, token_list

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1
    # order_list
    def test_normal_1(self, client, session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit order event
        bond_token, order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # add order event record
        order = Order()
        order.id = 1
        order.token_address = bond_token["address"]
        order.exchange_address = bond_exchange["address"]
        order.order_id = order_id
        order.unique_order_id = bond_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        # request target API
        request_params = {
            "exchange_contract_name": "IbetStraightBondExchange",
            "account_address_list": [account["account_address"]]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assumed_body = {
            "order_id": order_id,
            "counterpart_address": "",
            "amount": 1000000,
            "price": 1000,
            "is_buy": False,
            "canceled": False,
            "order_timestamp": "2019/06/17 00:00:00"
        }
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["order_list"]) >= 1
        for order in resp.json["data"]["order_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["order"] == assumed_body

    # Normal_2
    # settlement_list
    def test_normal_2(self, client, session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit agreement event
        bond_token, order_id, agreement_id = self.bond_agreement_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # add order event record
        order = Order()
        order.id = 1
        order.token_address = bond_token["address"]
        order.exchange_address = bond_exchange["address"]
        order.order_id = order_id
        order.unique_order_id = bond_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        # add agreement event record
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = bond_exchange["address"]
        agreement.unique_order_id = bond_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        session.add(agreement)

        # request target API
        request_params = {
            "exchange_contract_name": "IbetStraightBondExchange",
            "account_address_list": [account["account_address"]]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assumed_body = {
            "agreement": {
                "exchange_address": bond_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00"
            }
        }
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["settlement_list"]) >= 1
        for order in resp.json["data"]["settlement_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["agreement"] == assumed_body["agreement"]

    # Normal_3
    # complete_list
    def test_normal_3(self, client, session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit settlement event
        bond_token, order_id, agreement_id = self.bond_settlement_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # add order event record
        order = Order()
        order.id = 1
        order.token_address = bond_token["address"]
        order.exchange_address = bond_exchange["address"]
        order.order_id = order_id
        order.unique_order_id = bond_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        # add agreement event record
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = bond_exchange["address"]
        agreement.unique_order_id = bond_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        # request target API
        request_params = {
            "exchange_contract_name": "IbetStraightBondExchange",
            "account_address_list": [account["account_address"]]
        }
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assumed_body = {
            "agreement": {
                "exchange_address": bond_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "agreement_timestamp": "2019/06/17 12:00:00"
            },
            "settlement_timestamp": "2019/06/18 00:00:00"
        }
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["complete_list"]) >= 1
        for order in resp.json["data"]["complete_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["agreement"] == assumed_body["agreement"]
                assert order["settlement_timestamp"] == assumed_body["settlement_timestamp"]

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # invalid token address
    # -> 400
    def test_error_1(self, client):
        # request target API
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})
        resp = client.simulate_post(
            self.base_url + "invalid_token_address",
            headers=headers,
            body=request_body
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid token_address"
        }

    # Error_2
    # No headers
    # -> 400
    def test_error_2(self, client, shared_contract):
        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit order event
        bond_token, order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # request target API
        headers = {}
        request_body = json.dumps({})
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # Error_3_1
    # Validation error: no request-body
    # -> 400
    def test_error_3_1(self, client, shared_contract):
        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit order event
        bond_token, order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # request target API
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "exchange_contract_name": "required field",
                "account_address_list": "required field"
            }
        }

    # Error_3_2
    # Validation error: invalid type (exchange_contract_name)
    # -> 400
    def test_error_3_2(self, client, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit order event
        bond_token, order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # request target API
        headers = {"Content-Type": "application/json"}
        request_params = {
            "exchange_contract_name": "invalid_contract_name",
            "account_address_list": [account["account_address"]]
        }
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "exchange_contract_name": "unallowed value invalid_contract_name"
            }
        }

    # Error_3_3
    # Validation error: invalid type (account_address)
    # -> 400
    def test_error_3_3(self, client, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        # emit order event
        bond_token, order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            payment_gateway=payment_gateway,
            token_list=token_list
        )

        # request target API
        headers = {"Content-Type": "application/json"}
        request_params = {
            "exchange_contract_name": "IbetStraightBondExchange",
            "account_address_list": [account["account_address"][:-1]]
        }
        request_body = json.dumps(request_params)
        resp = client.simulate_post(
            self.base_url + bond_token["address"],
            headers=headers,
            body=request_body
        )

        # assertion
        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": "invalid account address"
        }


class TestV2OrderListBond:
    """
    Test Case for v2.order_list.StraightBondOrderList
    """

    # テスト対象API
    apiurl = "/v2/OrderList/StraightBond"

    @staticmethod
    def bond_token_attribute(exchange, personal_info):
        attribute = {
            "name": "テスト債券",
            "symbol": "BOND",
            "totalSupply": 1000000,
            "tradableExchange": exchange["address"],
            "faceValue": 10000,
            "interestRate": 602,
            "interestPaymentDate1": "0101",
            "interestPaymentDate2": "0201",
            "interestPaymentDate3": "0301",
            "interestPaymentDate4": "0401",
            "interestPaymentDate5": "0501",
            "interestPaymentDate6": "0601",
            "interestPaymentDate7": "0701",
            "interestPaymentDate8": "0801",
            "interestPaymentDate9": "0901",
            "interestPaymentDate10": "1001",
            "interestPaymentDate11": "1101",
            "interestPaymentDate12": "1201",
            "redemptionDate": "20191231",
            "redemptionValue": 10000,
            "returnDate": "20191231",
            "returnAmount": "商品券をプレゼント",
            "purpose": "新商品の開発資金として利用。",
            "memo": "メモ",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "personalInfoAddress": personal_info["address"]
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]

        attribute = TestV2OrderListBond.bond_token_attribute(bond_exchange, personal_info)

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

        order_id = get_latest_orderid(bond_exchange)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestV2OrderListBond.bond_token_attribute(bond_exchange, personal_info)

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
        order_id = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, order_id, 100)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(bond_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestV2OrderListBond.bond_token_attribute(bond_exchange, personal_info)

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
        order_id = get_latest_orderid(bond_exchange)
        take_buy_bond_token(trader, bond_exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = get_latest_agreementid(bond_exchange, order_id)
        bond_confirm_agreement(agent, bond_exchange, order_id, agreement_id)

        return bond_token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract["IbetStraightBondExchange"]
        membership_exchange = shared_contract["IbetMembershipExchange"]
        coupon_exchange = shared_contract["IbetCouponExchange"]
        personal_info = shared_contract["PersonalInfo"]
        payment_gateway = shared_contract["PaymentGateway"]
        token_list = shared_contract["TokenList"]
        config.BOND_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange["address"]
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, personal_info, payment_gateway, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)
        bond_token, order_id, agreement_id = self.order_event(
            bond_exchange, personal_info, payment_gateway, token_list)

        account = eth_account["issuer"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = bond_token["address"]
        order.exchange_address = bond_exchange["address"]
        order.order_id = order_id
        order.unique_order_id = bond_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "isRedeemed": False,
                "transferable": True,
                "image_url": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "certification": [],
                "initial_offering_status": False,
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": False,
                "order_timestamp": "2019/06/17 00:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["order_list"]) >= 1
        for order in resp.json["data"]["order_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)
        bond_token, order_id, agreement_id = self.agreement_event(
            bond_exchange, personal_info, payment_gateway, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = bond_exchange["address"]
        agreement.unique_order_id = bond_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "isRedeemed": False,
                "transferable": True,
                "image_url": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "certification": [],
                "initial_offering_status": False,
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": bond_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["settlement_list"]) >= 1
        for order in resp.json["data"]["settlement_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)
        bond_token, order_id, agreement_id = self.settlement_event(
            bond_exchange, personal_info, payment_gateway, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = bond_exchange["address"]
        agreement.unique_order_id = bond_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": bond_token["address"],
                "token_template": "IbetStraightBond",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト債券",
                "symbol": "BOND",
                "total_supply": 1000000,
                "face_value": 10000,
                "interest_rate": 0.0602,
                "interest_payment_date1": "0101",
                "interest_payment_date2": "0201",
                "interest_payment_date3": "0301",
                "interest_payment_date4": "0401",
                "interest_payment_date5": "0501",
                "interest_payment_date6": "0601",
                "interest_payment_date7": "0701",
                "interest_payment_date8": "0801",
                "interest_payment_date9": "0901",
                "interest_payment_date10": "1001",
                "interest_payment_date11": "1101",
                "interest_payment_date12": "1201",
                "redemption_date": "20191231",
                "redemption_value": 10000,
                "return_date": "20191231",
                "return_amount": "商品券をプレゼント",
                "purpose": "新商品の開発資金として利用。",
                "isRedeemed": False,
                "transferable": True,
                "image_url": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "certification": [],
                "initial_offering_status": False,
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": bond_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "agreement_timestamp": "2019/06/17 12:00:00"
            },
            "settlement_timestamp": "2019/06/18 00:00:00"
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["complete_list"]) >= 1
        for order in resp.json["data"]["complete_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert order["settlement_timestamp"] == assumed_body["settlement_timestamp"]

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_error_1(self, client):
        config.BOND_TOKEN_ENABLED = True
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": "required field"
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_error_2(self, client):
        config.BOND_TOKEN_ENABLED = True
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_error_3_1(self, client):
        config.BOND_TOKEN_ENABLED = True
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_error_3_2(self, client):
        config.BOND_TOKEN_ENABLED = True
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": {
                    "0": "must be of string type"
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_error_4(self, client):
        config.BOND_TOKEN_ENABLED = True
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /v2/OrderList/StraightBond"
        }

    # ＜エラー系5＞
    # 取扱トークン対象外(ENABLED=false)
    def test_error_5(self, client):
        config.BOND_TOKEN_ENABLED = False
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/StraightBond"
        }

    # ＜エラー系6＞
    # exchangeアドレス未設定
    def test_error_6(self, client):
        config.BOND_TOKEN_ENABLED = True
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = None
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/StraightBond"
        }


class TestV2OrderListMembership:
    """
    Test Case for v2.order_list.MembershipOrderList
    """

    # テスト対象API
    apiurl = "/v2/OrderList/Membership"

    @staticmethod
    def membership_token_attribute(exchange):
        attribute = {
            "name": "テスト会員権",
            "symbol": "MEMBERSHIP",
            "initialSupply": 1000000,
            "tradableExchange": exchange["address"],
            "details": "詳細",
            "returnDetails": "リターン詳細",
            "expirationDate": "20191231",
            "memo": "メモ",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー"
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(exchange, token_list):
        issuer = eth_account["issuer"]

        attribute = TestV2OrderListMembership. \
            membership_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        order_id = membership_get_latest_orderid(exchange)
        agreement_id = membership_get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestV2OrderListMembership. \
            membership_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, order_id, 100)
        agreement_id = membership_get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestV2OrderListMembership. \
            membership_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = membership_get_latest_orderid(exchange)
        membership_take_buy(trader, exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = membership_get_latest_agreementid(exchange, order_id)
        membership_confirm_agreement(agent, exchange, order_id, agreement_id)

        return token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract["IbetStraightBondExchange"]
        membership_exchange = shared_contract["IbetMembershipExchange"]
        coupon_exchange = shared_contract["IbetCouponExchange"]
        token_list = shared_contract["TokenList"]
        config.BOND_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange["address"]
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            self.set_env(shared_contract)

        token, order_id, agreement_id = \
            self.order_event(membership_exchange, token_list)

        account = eth_account["issuer"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = token["address"]
        order.exchange_address = membership_exchange["address"]
        order.order_id = 1
        order.unique_order_id = membership_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": token["address"],
                "token_template": "IbetMembership",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト会員権",
                "symbol": "MEMBERSHIP",
                "total_supply": 1000000,
                "details": "詳細",
                "return_details": "リターン詳細",
                "expiration_date": "20191231",
                "memo": "メモ",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "image_url": [
                    {"id": 1, "url": ""},
                    {"id": 2, "url": ""},
                    {"id": 3, "url": ""}
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": False,
                "order_timestamp": "2019/06/17 00:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、order_listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["order_list"]) >= 1
        for order in resp.json["data"]["order_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            self.set_env(shared_contract)

        token, order_id, agreement_id = \
            self.agreement_event(
                membership_exchange, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = membership_exchange["address"]
        agreement.unique_order_id = membership_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": token["address"],
                "token_template": "IbetMembership",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト会員権",
                "symbol": "MEMBERSHIP",
                "total_supply": 1000000,
                "details": "詳細",
                "return_details": "リターン詳細",
                "expiration_date": "20191231",
                "memo": "メモ",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "image_url": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": membership_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["settlement_list"]) >= 1
        for order in resp.json["data"]["settlement_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            self.set_env(shared_contract)

        token, order_id, agreement_id = \
            self.settlement_event(membership_exchange, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = membership_exchange["address"]
        agreement.unique_order_id = membership_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": token["address"],
                "token_template": "IbetMembership",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト会員権",
                "symbol": "MEMBERSHIP",
                "total_supply": 1000000,
                "details": "詳細",
                "return_details": "リターン詳細",
                "expiration_date": "20191231",
                "memo": "メモ",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "image_url": [
                    {"id": 1, "url": ""},
                    {"id": 2, "url": ""},
                    {"id": 3, "url": ""}
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": membership_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "agreement_timestamp": "2019/06/17 12:00:00"
            },
            "settlement_timestamp": "2019/06/18 00:00:00"
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["complete_list"]) >= 1
        for order in resp.json["data"]["complete_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert order["settlement_timestamp"] == assumed_body["settlement_timestamp"]

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_error_1(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": "required field"
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_error_2(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_error_3_1(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_error_3_2(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": {
                    "0": "must be of string type"
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_error_4(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /v2/OrderList/Membership"
        }

    # ＜エラー系5＞
    # 取扱トークン対象外(ENABLED=false)
    def test_error_5(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = False
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/Membership"
        }

    # ＜エラー系6＞
    # exchangeアドレス未設定
    def test_error_6(self, client):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/Membership"
        }


class TestV2OrderListCoupon:
    """
    Test Case for v2.order_list.CouponOrderList
    """

    # テスト対象API
    apiurl = "/v2/OrderList/Coupon"

    @staticmethod
    def coupon_token_attribute(exchange):
        attribute = {
            "name": "テストクーポン",
            "symbol": "COUPON",
            "totalSupply": 1000000,
            "tradableExchange": exchange["address"],
            "details": "クーポン詳細",
            "returnDetails": "リターン詳細",
            "memo": "クーポンメモ欄",
            "expirationDate": "20191231",
            "transferable": True,
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー"
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(exchange, token_list):
        issuer = eth_account["issuer"]

        attribute = TestV2OrderListCoupon.coupon_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        order_id = coupon_get_latest_orderid(exchange)
        agreement_id = coupon_get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestV2OrderListCoupon.coupon_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, order_id, 100)
        agreement_id = coupon_get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestV2OrderListCoupon.coupon_token_attribute(exchange)

        # ＜発行体オペレーション＞
        #   1) トークン発行
        #   2) トークンをトークンリストに登録
        #   3) 募集
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 買い注文
        order_id = coupon_get_latest_orderid(exchange)
        coupon_take_buy(trader, exchange, order_id, 100)

        # ＜決済業者オペレーション＞
        agreement_id = coupon_get_latest_agreementid(exchange, order_id)
        coupon_confirm_agreement(agent, exchange, order_id, agreement_id)

        return token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract["IbetStraightBondExchange"]
        membership_exchange = shared_contract["IbetMembershipExchange"]
        coupon_exchange = shared_contract["IbetCouponExchange"]
        token_list = shared_contract["TokenList"]
        config.BOND_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange["address"]
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    def test_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            self.set_env(shared_contract)

        token, order_id, agreement_id = \
            self.order_event(coupon_exchange, token_list)

        account = eth_account["issuer"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = token["address"]
        order.exchange_address = coupon_exchange["address"]
        order.order_id = 1
        order.unique_order_id = coupon_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = ""
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": token["address"],
                "token_template": "IbetCoupon",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テストクーポン",
                "symbol": "COUPON",
                "total_supply": 1000000,
                "details": "クーポン詳細",
                "return_details": "リターン詳細",
                "expiration_date": "20191231",
                "memo": "クーポンメモ欄",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "image_url": [
                    {"id": 1, "url": ""},
                    {"id": 2, "url": ""},
                    {"id": 3, "url": ""}
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": False,
                "order_timestamp": "2019/06/17 00:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、order_listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["order_list"]) >= 1
        for order in resp.json["data"]["order_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            self.set_env(shared_contract)

        token, order_id, agreement_id = \
            self.agreement_event(coupon_exchange, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = coupon_exchange["address"]
        agreement.unique_order_id = coupon_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": token["address"],
                "token_template": "IbetCoupon",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テストクーポン",
                "symbol": "COUPON",
                "total_supply": 1000000,
                "details": "クーポン詳細",
                "return_details": "リターン詳細",
                "expiration_date": "20191231",
                "memo": "クーポンメモ欄",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "image_url": [
                    {"id": 1, "url": ""},
                    {"id": 2, "url": ""},
                    {"id": 3, "url": ""}
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": coupon_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["settlement_list"]) >= 1
        for order in resp.json["data"]["settlement_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, token_list = \
            self.set_env(shared_contract)

        token, order_id, agreement_id = \
            self.settlement_event(coupon_exchange, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = coupon_exchange["address"]
        agreement.unique_order_id = coupon_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": token["address"],
                "token_template": "IbetCoupon",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テストクーポン",
                "symbol": "COUPON",
                "total_supply": 1000000,
                "details": "クーポン詳細",
                "return_details": "リターン詳細",
                "expiration_date": "20191231",
                "memo": "クーポンメモ欄",
                "transferable": True,
                "status": True,
                "initial_offering_status": False,
                "image_url": [
                    {"id": 1, "url": ""},
                    {"id": 2, "url": ""},
                    {"id": 3, "url": ""}
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": coupon_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "agreement_timestamp": "2019/06/17 12:00:00"
            },
            "settlement_timestamp": "2019/06/18 00:00:00"
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["complete_list"]) >= 1
        for order in resp.json["data"]["complete_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert order["settlement_timestamp"] == assumed_body["settlement_timestamp"]

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_error_1(self, client):
        config.COUPON_TOKEN_ENABLED = True
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": "required field"
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_error_2(self, client):
        config.COUPON_TOKEN_ENABLED = True
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_error_3_1(self, client):
        config.COUPON_TOKEN_ENABLED = True
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_error_3_2(self, client):
        config.COUPON_TOKEN_ENABLED = True
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": {
                    "0": "must be of string type"
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_error_4(self, client):
        config.COUPON_TOKEN_ENABLED = True
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /v2/OrderList/Coupon"
        }

    # ＜エラー系5＞
    # 取扱トークン対象外(ENABLED=false)
    def test_error_5(self, client):
        config.COUPON_TOKEN_ENABLED = False
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/Coupon"
        }

    # ＜エラー系6＞
    # exchangeアドレス未設定
    def test_error_6(self, client):
        config.COUPON_TOKEN_ENABLED = True
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = None
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/Coupon"
        }


class TestV2OrderListShare:
    """
    Test Case for v2.order_list.ShareOrderList
    """

    # テスト対象API
    apiurl = "/v2/OrderList/Share"

    @staticmethod
    def share_token_attribute(exchange, personal_info):
        attribute = {
            "name": "テスト株式",
            "symbol": "SHARE",
            "tradableExchange": exchange["address"],
            "personalInfoAddress": personal_info["address"],
            "issuePrice": 1000,
            "principalValue": 1000,
            "totalSupply": 1000000,
            "dividends": 101,
            "dividendRecordDate": "20200401",
            "dividendPaymentDate": "20200502",
            "cancellationDate": "20200603",
            "contactInformation": "問い合わせ先",
            "privacyPolicy": "プライバシーポリシー",
            "memo": "メモ",
            "transferable": True
        }
        return attribute

    # 注文中明細の作成：発行体
    @staticmethod
    def order_event(share_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestV2OrderListShare.share_token_attribute(share_exchange, personal_info)

        # ＜発行体オペレーション＞
        #   1) 株式トークン発行
        #   2) 株式トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) 募集
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        share_offer(issuer, share_exchange, share_token, trader, 1000000, 1000)

        order_id = get_latest_orderid(share_exchange)
        agreement_id = get_latest_agreementid(share_exchange, order_id)

        return share_token, order_id, agreement_id

    # 約定明細（決済中）の作成：投資家
    @staticmethod
    def agreement_event(share_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestV2OrderListShare.share_token_attribute(share_exchange, personal_info)

        # ＜発行体オペレーション＞
        #   1) 株式トークン発行
        #   2) 株式トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) Make売り
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        share_offer(issuer, share_exchange, share_token, trader, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) 収納代行コントラクト（PaymentGateway）に投資家の情報を登録
        #   3) 買い注文
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        order_id = get_latest_orderid(share_exchange)
        share_take_buy(trader, share_exchange, order_id)
        agreement_id = get_latest_agreementid(share_exchange, order_id)

        return share_token, order_id, agreement_id

    # 決済済明細の作成：決済業者
    @staticmethod
    def settlement_event(share_exchange, personal_info, payment_gateway, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestV2OrderListShare.share_token_attribute(share_exchange, personal_info)

        # ＜発行体オペレーション＞
        #   1) 株式トークン発行
        #   2) 株式トークンをトークンリストに登録
        #   3) 投資家名簿用個人情報コントラクト（PersonalInfo）に発行体の情報を登録
        #   4) 収納代行コントラクト（PaymentGateway）に発行体の情報を登録
        #   5) Make売り
        share_token = issue_share_token(issuer, attribute)
        register_share_list(issuer, share_token, token_list)
        register_personalinfo(issuer, personal_info)
        register_payment_gateway(issuer, payment_gateway)
        share_offer(issuer, share_exchange, share_token, trader, 1000000, 1000)

        # ＜投資家オペレーション＞
        #   1) 投資家名簿用個人情報コントラクト（PersonalInfo）に投資家の情報を登録
        #   2) 収納代行コントラクト（PaymentGateway）に投資家の情報を登録
        #   3) 買い注文
        register_personalinfo(trader, personal_info)
        register_payment_gateway(trader, payment_gateway)
        order_id = get_latest_orderid(share_exchange)
        share_take_buy(trader, share_exchange, order_id)

        # ＜決済業者オペレーション＞
        agreement_id = get_latest_agreementid(share_exchange, order_id)
        share_confirm_agreement(
            agent, share_exchange, order_id, agreement_id)

        return share_token, order_id, agreement_id

    @staticmethod
    def set_env(shared_contract):
        bond_exchange = shared_contract["IbetStraightBondExchange"]
        membership_exchange = shared_contract["IbetMembershipExchange"]
        coupon_exchange = shared_contract["IbetCouponExchange"]
        share_exchange = shared_contract["IbetOTCExchange"]
        personal_info = shared_contract["PersonalInfo"]
        payment_gateway = shared_contract["PaymentGateway"]
        token_list = shared_contract["TokenList"]
        config.BOND_TOKEN_ENABLED = True
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.COUPON_TOKEN_ENABLED = True
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS = bond_exchange["address"]
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange["address"]
        config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = share_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, share_exchange, personal_info, payment_gateway, token_list

    # ＜正常系1＞
    # 注文中あり（1件）、決済中なし、約定済なし
    #  -> order_listが1件返却
    # makerからのリクエストにおいてもorder_listが1件返却される
    def test_normal_1(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, share_exchange, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)
        share_token, order_id, agreement_id = self.order_event(
            share_exchange, personal_info, payment_gateway, token_list)

        account = eth_account["issuer"]
        counterpart = eth_account["trader"]

        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Orderイベント情報を挿入
        order = Order()
        order.id = 1
        order.token_address = share_token["address"]
        order.exchange_address = share_exchange["address"]
        order.order_id = order_id
        order.unique_order_id = share_exchange["address"] + "_" + str(1)
        order.account_address = account["account_address"]
        order.counterpart_address = counterpart["account_address"]
        order.is_buy = False
        order.price = 1000
        order.amount = 100
        order.agent_address = eth_account["agent"]["account_address"]
        order.is_cancelled = False
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": share_token["address"],
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": counterpart["account_address"],
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": False,
                "order_timestamp": "2019/06/17 00:00:00"
            }
        }

        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["order_list"]) >= 1
        for order in resp.json["data"]["order_list"]:
            if order["token"]["token_address"] == share_token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # ＜正常系2＞
    # 注文中なし、決済中あり（1件）、約定済なし
    #  -> settlement_listが1件返却
    def test_normal_2(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, share_exchange, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        share_token, order_id, agreement_id = self.\
            agreement_event(share_exchange, personal_info, payment_gateway, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = share_exchange["address"]
        agreement.unique_order_id = share_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.PENDING.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": share_token["address"],
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": share_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 1000000,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00"
            }
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["settlement_list"]) >= 1
        for order in resp.json["data"]["settlement_list"]:
            if order["token"]["token_address"] == share_token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]

    # ＜正常系3＞
    # 注文中なし、決済中なし、約定済あり（1件）
    #  -> complete_listが1件返却
    def test_normal_3(self, client, session, shared_contract):
        bond_exchange, membership_exchange, coupon_exchange, share_exchange, personal_info, payment_gateway, token_list = \
            self.set_env(shared_contract)

        share_token, order_id, agreement_id = self.\
            settlement_event(share_exchange, personal_info, payment_gateway, token_list)

        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        # Agreementイベント情報を挿入
        agreement = Agreement()
        agreement.id = 1
        agreement.order_id = order_id
        agreement.agreement_id = agreement_id
        agreement.exchange_address = share_exchange["address"]
        agreement.unique_order_id = share_exchange["address"] + "_" + str(1)
        agreement.buyer_address = account["account_address"]
        agreement.seller_address = ""
        agreement.counterpart_address = ""
        agreement.amount = 100
        agreement.status = AgreementStatus.DONE.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assumed_body = {
            "token": {
                "token_address": share_token["address"],
                "token_template": "IbetShare",
                "owner_address": eth_account["issuer"]["account_address"],
                "company_name": "",
                "rsa_publickey": "",
                "name": "テスト株式",
                "symbol": "SHARE",
                "total_supply": 1000000,
                "issue_price": 1000,
                "principal_value": 1000,
                "dividend_information": {
                    "dividends": 1.01,
                    "dividend_record_date": "20200401",
                    "dividend_payment_date": "20200502"
                },
                "cancellation_date": "20200603",
                "memo": "メモ",
                "transferable": True,
                "offering_status": False,
                "status": True,
                "transfer_approval_required": False,
                "is_canceled": False,
                "reference_urls": [{
                    "id": 1,
                    "url": ""
                }, {
                    "id": 2,
                    "url": ""
                }, {
                    "id": 3,
                    "url": ""
                }],
                "image_url": [],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー"
            },
            "agreement": {
                "exchange_address": share_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 1000000,
                "price": 1000,
                "is_buy": True,
                "agreement_timestamp": "2019/06/17 12:00:00"
            },
            "settlement_timestamp": "2019/06/18 00:00:00"
        }

        # NOTE: 他のテストで注文を出している可能性があるので、listは１件ではない場合がある。
        # API内部でエラー発生すると、正常応答でlistが0件になる場合もある。
        assert resp.status_code == 200
        assert resp.json["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json["data"]["complete_list"]) >= 1
        for order in resp.json["data"]["complete_list"]:
            if order["token"]["token_address"] == share_token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert order["settlement_timestamp"] == assumed_body["settlement_timestamp"]

    # ＜エラー系1＞
    # request-bodyなし
    # -> 入力値エラー
    def test_error_1(self, client):
        config.SHARE_TOKEN_ENABLED = True
        headers = {"Content-Type": "application/json"}
        request_body = json.dumps({})

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": "required field"
            }
        }

    # ＜エラー系2＞
    # headersなし
    # -> 入力値エラー
    def test_error_2(self, client):
        config.SHARE_TOKEN_ENABLED = True
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}

        headers = {}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-1＞
    # account_addressがアドレスフォーマットではない
    # -> 入力値エラー
    def test_error_3_1(self, client):
        config.SHARE_TOKEN_ENABLED = True
        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # アドレスが短い
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter"
        }

    # ＜エラー系3-2＞
    # account_addressがstring以外
    # -> 入力エラー
    def test_error_3_2(self, client):
        config.SHARE_TOKEN_ENABLED = True
        account_address = 123456789123456789123456789123456789
        request_params = {"account_address_list": [account_address]}

        headers = {"Content-Type": "application/json"}
        request_body = json.dumps(request_params)

        resp = client.simulate_post(
            self.apiurl, headers=headers, body=request_body)

        assert resp.status_code == 400
        assert resp.json["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": {
                "account_address_list": {
                    "0": "must be of string type"
                }
            }
        }

    # ＜エラー系4＞
    # HTTPメソッドが不正
    def test_error_4(self, client):
        config.SHARE_TOKEN_ENABLED = True
        resp = client.simulate_get(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /v2/OrderList/Share"
        }

    # ＜エラー系5＞
    # 取扱トークン対象外(ENABLED=false)
    def test_error_5(self, client):
        config.SHARE_TOKEN_ENABLED = False
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/Share"
        }

    # ＜エラー系6＞
    # exchangeアドレス未設定
    def test_error_6(self, client):
        config.SHARE_TOKEN_ENABLED = True
        config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS = None
        resp = client.simulate_post(self.apiurl)

        assert resp.status_code == 404
        assert resp.json["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: POST, url: /v2/OrderList/Share"
        }
