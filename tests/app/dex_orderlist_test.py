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

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from app import config
from app.model.db import AgreementStatus, IDXAgreement as Agreement, IDXOrder as Order
from tests.contract_modules import (
    cancel_agreement,
    cancel_order,
    confirm_agreement,
    coupon_offer,
    coupon_register_list,
    eth_account,
    get_latest_agreementid,
    get_latest_orderid,
    issue_bond_token,
    issue_coupon_token,
    membership_issue,
    membership_offer,
    membership_register_list,
    offer_bond_token,
    register_bond_list,
    take_buy,
)
from tests.utils import PersonalInfoUtils as pi_utils

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)


class TestDEXOrderList:
    # Test target API
    base_url = "/DEX/OrderList/"

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
            "personalInfoAddress": personal_info["address"],
            "faceValueCurrency": "JPY",
            "interestPaymentCurrency": "JPY",
            "redemptionValueCurrency": "JPY",
            "baseFxRate": "",
        }
        return attribute

    # Emit NewOrder event
    @staticmethod
    def bond_order_event(bond_exchange, personal_info, token_list):
        issuer = eth_account["issuer"]
        attribute = TestDEXOrderList.bond_token_attribute(bond_exchange, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)
        order_id = get_latest_orderid(bond_exchange)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # Emit CancelOrder event
    @staticmethod
    def bond_cancel_order_event(bond_exchange, personal_info, token_list):
        issuer = eth_account["issuer"]
        attribute = TestDEXOrderList.bond_token_attribute(bond_exchange, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)
        order_id = get_latest_orderid(bond_exchange)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)
        cancel_order(issuer, bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # Emit Agree event
    @staticmethod
    def bond_agreement_event(bond_exchange, personal_info, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        attribute = TestDEXOrderList.bond_token_attribute(bond_exchange, personal_info)
        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        order_id = get_latest_orderid(bond_exchange)
        take_buy(trader, bond_exchange, order_id, 100)
        agreement_id = get_latest_agreementid(bond_exchange, order_id)

        return bond_token, order_id, agreement_id

    # Emit SettlementOK event
    @staticmethod
    def bond_settlement_ok_event(bond_exchange, personal_info, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestDEXOrderList.bond_token_attribute(bond_exchange, personal_info)

        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        pi_utils.register(
            trader["account_address"],
            personal_info["address"],
            issuer["account_address"],
        )
        order_id = get_latest_orderid(bond_exchange)
        take_buy(trader, bond_exchange, order_id, 100)

        agreement_id = get_latest_agreementid(bond_exchange, order_id)
        confirm_agreement(agent, bond_exchange, order_id, agreement_id)

        return bond_token, order_id, agreement_id

    # Emit SettlementOK event
    @staticmethod
    def bond_settlement_ng_event(bond_exchange, personal_info, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        attribute = TestDEXOrderList.bond_token_attribute(bond_exchange, personal_info)

        bond_token = issue_bond_token(issuer, attribute)
        register_bond_list(issuer, bond_token, token_list)
        offer_bond_token(issuer, bond_exchange, bond_token, 1000000, 1000)

        pi_utils.register(
            trader["account_address"],
            personal_info["address"],
            issuer["account_address"],
        )
        order_id = get_latest_orderid(bond_exchange)
        take_buy(trader, bond_exchange, order_id, 100)

        agreement_id = get_latest_agreementid(bond_exchange, order_id)
        cancel_agreement(agent, bond_exchange, order_id, agreement_id)

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
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange[
            "address"
        ]
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return (
            bond_exchange,
            membership_exchange,
            coupon_exchange,
            personal_info,
            payment_gateway,
            token_list,
        )

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1_1
    # order_list
    def test_normal_1_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        bond_exchange, _, _, personal_info, _, token_list = self.set_env(
            shared_contract
        )

        # emit NewOrder event
        bond_token, order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            token_list=token_list,
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.base_url + bond_token["address"], params=request_params)

        # assertion
        assumed_body = {
            "order_id": order_id,
            "counterpart_address": "",
            "amount": 1000000,
            "price": 1000,
            "is_buy": False,
            "canceled": False,
            "order_timestamp": "2019/06/17 00:00:00",
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["order_list"]) >= 1
        for order in resp.json()["data"]["order_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["order"] == assumed_body

    # Normal_1_2
    # order_list(canceled)
    def test_normal_1_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        bond_exchange, _, _, personal_info, _, token_list = self.set_env(
            shared_contract
        )

        # emit CancelOrder event
        bond_token, order_id, _ = self.bond_cancel_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            token_list=token_list,
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
        order.is_cancelled = True
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        session.commit()

        # request target API
        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": True,
        }
        resp = client.get(self.base_url + bond_token["address"], params=request_params)

        # assertion
        assumed_body = {
            "order_id": order_id,
            "counterpart_address": "",
            "amount": 1000000,
            "price": 1000,
            "is_buy": False,
            "canceled": True,
            "order_timestamp": "2019/06/17 00:00:00",
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["order_list"]) >= 1
        for order in resp.json()["data"]["order_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["order"] == assumed_body

    # Normal_2
    # settlement_list
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, _, token_list = self.set_env(
            shared_contract
        )

        # emit Agree event
        bond_token, order_id, agreement_id = self.bond_agreement_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            token_list=token_list,
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.base_url + bond_token["address"], params=request_params)

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
                "agreement_timestamp": "2019/06/17 12:00:00",
            }
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["settlement_list"]) >= 1
        for order in resp.json()["data"]["settlement_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["agreement"] == assumed_body["agreement"]

    # Normal_3_1
    # complete_list
    def test_normal_3_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, _, token_list = self.set_env(
            shared_contract
        )

        # emit SettlementOK event
        bond_token, order_id, agreement_id = self.bond_settlement_ok_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            token_list=token_list,
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.base_url + bond_token["address"], params=request_params)

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
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
            "settlement_timestamp": "2019/06/18 00:00:00",
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["complete_list"]) >= 1
        for order in resp.json()["data"]["complete_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["agreement"] == assumed_body["agreement"]
                assert (
                    order["settlement_timestamp"]
                    == assumed_body["settlement_timestamp"]
                )

    # Normal_3_2
    # complete_list(canceled)
    def test_normal_3_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, _, token_list = self.set_env(
            shared_contract
        )

        # emit SettlementNG event
        bond_token, order_id, agreement_id = self.bond_settlement_ng_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            token_list=token_list,
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
        agreement.status = AgreementStatus.CANCELED.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        session.commit()

        # request target API
        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": True,
        }
        resp = client.get(self.base_url + bond_token["address"], params=request_params)

        # assertion
        assumed_body = {
            "agreement": {
                "exchange_address": bond_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": True,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
            "settlement_timestamp": "2019/06/18 00:00:00",
        }
        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["complete_list"]) >= 1
        for order in resp.json()["data"]["complete_list"]:
            if order["token"]["token_address"] == bond_token["address"]:
                assert order["agreement"] == assumed_body["agreement"]
                assert (
                    order["settlement_timestamp"]
                    == assumed_body["settlement_timestamp"]
                )

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # account_address_list has not a valid address
    # Invalid Parameter
    def test_error_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        bond_exchange, _, _, personal_info, _, token_list = self.set_env(
            shared_contract
        )

        # emit NewOrder event
        bond_token, _order_id, _ = self.bond_order_event(
            bond_exchange=bond_exchange,
            personal_info=personal_info,
            token_list=token_list,
        )

        # request target API
        request_params = {"account_address_list": [account["account_address"][:-1]]}
        resp = client.get(self.base_url + bond_token["address"], params=request_params)

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "account_address_list", 0],
                    "msg": "Value error, Invalid ethereum address",
                    "input": account["account_address"][:-1],
                    "ctx": {"error": {}},
                }
            ],
        }


class TestDEXOrderListMembership:
    # Test target API
    apiurl = "/DEX/OrderList/Membership"

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
            "privacyPolicy": "プライバシーポリシー",
        }
        return attribute

    # Emit NewOrder event
    @staticmethod
    def order_event(exchange, token_list):
        issuer = eth_account["issuer"]

        # issue token
        attribute = TestDEXOrderListMembership.membership_token_attribute(exchange)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # make sell order
        membership_offer(issuer, exchange, token, 1000000, 1000)
        order_id = get_latest_orderid(exchange)
        agreement_id = get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # Emit CancelOrder event
    @staticmethod
    def cancel_order_event(exchange, token_list):
        issuer = eth_account["issuer"]

        # issue token
        attribute = TestDEXOrderListMembership.membership_token_attribute(exchange)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # make sell order
        membership_offer(issuer, exchange, token, 1000000, 1000)
        order_id = get_latest_orderid(exchange)
        agreement_id = get_latest_agreementid(exchange, order_id)

        # cancel order
        cancel_order(issuer, exchange, order_id)

        return token, order_id, agreement_id

    # Emit Agree event
    @staticmethod
    def agreement_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        # issue token
        attribute = TestDEXOrderListMembership.membership_token_attribute(exchange)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # make sell order
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # take buy order
        order_id = get_latest_orderid(exchange)
        take_buy(trader, exchange, order_id, 100)
        agreement_id = get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # Emit SettlementOK event
    @staticmethod
    def settlement_ok_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        # issue token
        attribute = TestDEXOrderListMembership.membership_token_attribute(exchange)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # make sell order
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # take buy order
        order_id = get_latest_orderid(exchange)
        take_buy(trader, exchange, order_id, 100)

        # confirm agreement
        agreement_id = get_latest_agreementid(exchange, order_id)
        confirm_agreement(agent, exchange, order_id, agreement_id)

        return token, order_id, agreement_id

    # Emit SettlementNG event
    @staticmethod
    def settlement_ng_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        # issue token
        attribute = TestDEXOrderListMembership.membership_token_attribute(exchange)
        token = membership_issue(issuer, attribute)
        membership_register_list(issuer, token, token_list)

        # make sell order
        membership_offer(issuer, exchange, token, 1000000, 1000)

        # take buy order
        order_id = get_latest_orderid(exchange)
        take_buy(trader, exchange, order_id, 100)

        # cancel agreement
        agreement_id = get_latest_agreementid(exchange, order_id)
        cancel_agreement(agent, exchange, order_id, agreement_id)

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
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange[
            "address"
        ]
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, token_list

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1_1
    # order_list
    def test_normal_1_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        _, membership_exchange, _, token_list = self.set_env(shared_contract)

        # emit NewOrder event
        token, order_id, _agreement_id = self.order_event(
            membership_exchange, token_list
        )

        # add order event record
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": membership_exchange["address"],
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": False,
                "order_timestamp": "2019/06/17 00:00:00",
            },
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["order_list"]) >= 1
        for order in resp.json()["data"]["order_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # Normal_1_2
    # order_list(canceled)
    def test_normal_1_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        _, membership_exchange, _, token_list = self.set_env(shared_contract)

        # emit CancelOrder event
        token, order_id, _agreement_id = self.order_event(
            membership_exchange, token_list
        )

        # add order event record
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
        order.is_cancelled = True
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        session.commit()

        # request target API
        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": True,
        }
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": membership_exchange["address"],
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": True,
                "order_timestamp": "2019/06/17 00:00:00",
            },
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["order_list"]) >= 1
        for order in resp.json()["data"]["order_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # Normal_2
    # settlement_list
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        _, membership_exchange, _, token_list = self.set_env(shared_contract)

        # emit Agree event
        token, order_id, agreement_id = self.agreement_event(
            exchange=membership_exchange, token_list=token_list
        )

        # add agreement event record
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": membership_exchange["address"],
            },
            "agreement": {
                "exchange_address": membership_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["settlement_list"]) >= 1
        for order in resp.json()["data"]["settlement_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]

    # Normal_3_1
    # complete_list
    def test_normal_3_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        _, membership_exchange, _, token_list = self.set_env(shared_contract)

        # emit SettlementOK event
        token, order_id, agreement_id = self.settlement_ok_event(
            exchange=membership_exchange, token_list=token_list
        )

        # add agreement event record
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": membership_exchange["address"],
            },
            "agreement": {
                "exchange_address": membership_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
            "settlement_timestamp": "2019/06/18 00:00:00",
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["complete_list"]) >= 1
        for order in resp.json()["data"]["complete_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert (
                    order["settlement_timestamp"]
                    == assumed_body["settlement_timestamp"]
                )

    # Normal_3_2
    # complete_list(canceled)
    def test_normal_3_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        _, membership_exchange, _, token_list = self.set_env(shared_contract)

        # emit SettlementNG event
        token, order_id, agreement_id = self.settlement_ng_event(
            exchange=membership_exchange, token_list=token_list
        )

        # add agreement event record
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
        agreement.status = AgreementStatus.CANCELED.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        session.commit()

        # request target API
        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": True,
        }
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": membership_exchange["address"],
            },
            "agreement": {
                "exchange_address": membership_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": True,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
            "settlement_timestamp": "2019/06/18 00:00:00",
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["complete_list"]) >= 1
        for order in resp.json()["data"]["complete_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert (
                    order["settlement_timestamp"]
                    == assumed_body["settlement_timestamp"]
                )

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # account_address_list has not a valid address
    # Invalid Parameter
    def test_error_1(self, client: TestClient, session: Session):
        config.MEMBERSHIP_TOKEN_ENABLED = True

        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # invalid address
        request_params = {"account_address_list": [account_address]}
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "account_address_list", 0],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0xeb6e99675595fb052cc68da0eeecb2d5a382637",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2
    # Validation error: include_canceled_items must be boolean
    # Invalid Parameter
    def test_error_2(self, client: TestClient, session: Session):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        account = eth_account["trader"]

        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": "test",
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "test",
                    "loc": ["query", "include_canceled_items"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "type": "bool_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3
    # Not supported HTTP method
    def test_error_3(self, client: TestClient, session: Session):
        config.MEMBERSHIP_TOKEN_ENABLED = True
        resp = client.post(self.apiurl)

        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: POST, url: /DEX/OrderList/Membership",
        }

    # Error_4
    # Membership token is not enabled
    def test_error_4(self, client: TestClient, session: Session):
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        config.MEMBERSHIP_TOKEN_ENABLED = False
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/OrderList/Membership",
        }

    # Error_5
    # Exchange address is not set
    def test_error_5(self, client: TestClient, session: Session):
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}
        config.MEMBERSHIP_TOKEN_ENABLED = True
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = None
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/OrderList/Membership",
        }


class TestDEXOrderListCoupon:
    # Test target API
    apiurl = "/DEX/OrderList/Coupon"

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
            "privacyPolicy": "プライバシーポリシー",
        }
        return attribute

    # Emit NewOrder event
    @staticmethod
    def order_event(exchange, token_list):
        issuer = eth_account["issuer"]

        attribute = TestDEXOrderListCoupon.coupon_token_attribute(exchange)

        # issue token
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # make sell order
        coupon_offer(issuer, exchange, token, 1000000, 1000)
        order_id = get_latest_orderid(exchange)
        agreement_id = get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # Emit CancelOrder event
    @staticmethod
    def cancel_order_event(exchange, token_list):
        issuer = eth_account["issuer"]

        attribute = TestDEXOrderListCoupon.coupon_token_attribute(exchange)

        # issue token
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # make sell order
        coupon_offer(issuer, exchange, token, 1000000, 1000)
        order_id = get_latest_orderid(exchange)
        agreement_id = get_latest_agreementid(exchange, order_id)

        # cancel order
        cancel_order(issuer, exchange, order_id)

        return token, order_id, agreement_id

    # Emit Agree event
    @staticmethod
    def agreement_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]

        # issue token
        attribute = TestDEXOrderListCoupon.coupon_token_attribute(exchange)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # make sell order
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # take buy ordder
        order_id = get_latest_orderid(exchange)
        take_buy(trader, exchange, order_id, 100)
        agreement_id = get_latest_agreementid(exchange, order_id)

        return token, order_id, agreement_id

    # Emit SettlementOK event
    @staticmethod
    def settlement_ok_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        # issue token
        attribute = TestDEXOrderListCoupon.coupon_token_attribute(exchange)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # make sell order
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # take buy order
        order_id = get_latest_orderid(exchange)
        take_buy(trader, exchange, order_id, 100)

        # confirm agreement
        agreement_id = get_latest_agreementid(exchange, order_id)
        confirm_agreement(agent, exchange, order_id, agreement_id)

        return token, order_id, agreement_id

    # Emit SettlementNG event
    @staticmethod
    def settlement_ng_event(exchange, token_list):
        issuer = eth_account["issuer"]
        trader = eth_account["trader"]
        agent = eth_account["agent"]

        # issue token
        attribute = TestDEXOrderListCoupon.coupon_token_attribute(exchange)
        token = issue_coupon_token(issuer, attribute)
        coupon_register_list(issuer, token, token_list)

        # make sell order
        coupon_offer(issuer, exchange, token, 1000000, 1000)

        # take buy order
        order_id = get_latest_orderid(exchange)
        take_buy(trader, exchange, order_id, 100)

        # confirm agreement
        agreement_id = get_latest_agreementid(exchange, order_id)
        cancel_agreement(agent, exchange, order_id, agreement_id)

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
        config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS = membership_exchange[
            "address"
        ]
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = coupon_exchange["address"]
        config.TOKEN_LIST_CONTRACT_ADDRESS = token_list["address"]
        return bond_exchange, membership_exchange, coupon_exchange, token_list

    ###########################################################################
    # Normal Case
    ###########################################################################

    # Normal_1_1
    # order_list
    def test_normal_1_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        _, _, coupon_exchange, token_list = self.set_env(shared_contract)

        # emit NewOrder event
        token, order_id, _agreement_id = self.order_event(coupon_exchange, token_list)

        # add order event
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": coupon_exchange["address"],
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": False,
                "order_timestamp": "2019/06/17 00:00:00",
            },
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["order_list"]) >= 1
        for order in resp.json()["data"]["order_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # Normal_1_2
    # order_list(canceled)
    def test_normal_1_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["issuer"]

        # set environment variables
        _, _, coupon_exchange, token_list = self.set_env(shared_contract)

        # emit CancelOrder event
        token, order_id, _agreement_id = self.cancel_order_event(
            coupon_exchange, token_list
        )

        # add order event
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
        order.is_cancelled = True
        order.order_timestamp = "2019-06-17 00:00:00"
        session.add(order)

        session.commit()

        # request target API
        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": True,
        }
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": coupon_exchange["address"],
            },
            "order": {
                "order_id": order_id,
                "counterpart_address": "",
                "amount": 1000000,
                "price": 1000,
                "is_buy": False,
                "canceled": True,
                "order_timestamp": "2019/06/17 00:00:00",
            },
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["order_list"]) >= 1
        for order in resp.json()["data"]["order_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["order"] == assumed_body["order"]

    # Normal_2
    # settlement_list
    def test_normal_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        _, _, coupon_exchange, token_list = self.set_env(shared_contract)

        # emit Agree event
        token, order_id, agreement_id = self.agreement_event(
            coupon_exchange, token_list
        )

        # add agreement event record
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": coupon_exchange["address"],
            },
            "agreement": {
                "exchange_address": coupon_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["settlement_list"]) >= 1
        for order in resp.json()["data"]["settlement_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]

    # Normal_3_1
    # complete_list
    def test_normal_3_1(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        _, _, coupon_exchange, token_list = self.set_env(shared_contract)

        # emit SettlementOK event
        token, order_id, agreement_id = self.settlement_ok_event(
            exchange=coupon_exchange, token_list=token_list
        )

        # add agreement event record
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

        session.commit()

        # request target API
        request_params = {"account_address_list": [account["account_address"]]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": coupon_exchange["address"],
            },
            "agreement": {
                "exchange_address": coupon_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": False,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
            "settlement_timestamp": "2019/06/18 00:00:00",
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["complete_list"]) >= 1
        for order in resp.json()["data"]["complete_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert (
                    order["settlement_timestamp"]
                    == assumed_body["settlement_timestamp"]
                )

    # Normal_3_2
    # complete_list(canceled)
    def test_normal_3_2(self, client: TestClient, session: Session, shared_contract):
        account = eth_account["trader"]

        # set environment variables
        _, _, coupon_exchange, token_list = self.set_env(shared_contract)

        # emit SettlementNG event
        token, order_id, agreement_id = self.settlement_ng_event(
            exchange=coupon_exchange, token_list=token_list
        )

        # add agreement event record
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
        agreement.status = AgreementStatus.CANCELED.value
        agreement.agreement_timestamp = "2019-06-17 12:00:00"
        agreement.settlement_timestamp = "2019-06-18 00:00:00"
        session.add(agreement)

        session.commit()

        # request target API
        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": True,
        }
        resp = client.get(self.apiurl, params=request_params)

        # assertion
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
                    {"id": 3, "url": ""},
                ],
                "max_holding_quantity": 0,
                "max_sell_amount": 0,
                "contact_information": "問い合わせ先",
                "privacy_policy": "プライバシーポリシー",
                "tradable_exchange": coupon_exchange["address"],
            },
            "agreement": {
                "exchange_address": coupon_exchange["address"],
                "order_id": order_id,
                "agreement_id": agreement_id,
                "amount": 100,
                "price": 1000,
                "is_buy": True,
                "canceled": True,
                "agreement_timestamp": "2019/06/17 12:00:00",
            },
            "settlement_timestamp": "2019/06/18 00:00:00",
        }

        assert resp.status_code == 200
        assert resp.json()["meta"] == {"code": 200, "message": "OK"}
        assert len(resp.json()["data"]["complete_list"]) >= 1
        for order in resp.json()["data"]["complete_list"]:
            if order["token"]["token_address"] == token["address"]:
                assert order["token"] == assumed_body["token"]
                assert order["agreement"] == assumed_body["agreement"]
                assert (
                    order["settlement_timestamp"]
                    == assumed_body["settlement_timestamp"]
                )

    ###########################################################################
    # Error Case
    ###########################################################################

    # Error_1
    # account_address_list has not a valid address
    # Invalid Parameter
    def test_error_1(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True

        account_address = "0xeb6e99675595fb052cc68da0eeecb2d5a382637"  # invalid address
        request_params = {"account_address_list": [account_address]}
        resp = client.get(self.apiurl, params=request_params)

        # assertion
        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "message": "Invalid Parameter",
            "description": [
                {
                    "type": "value_error",
                    "loc": ["query", "account_address_list", 0],
                    "msg": "Value error, Invalid ethereum address",
                    "input": "0xeb6e99675595fb052cc68da0eeecb2d5a382637",
                    "ctx": {"error": {}},
                }
            ],
        }

    # Error_2
    # Validation error: include_canceled_items must be boolean
    # Invalid Parameter
    def test_error_2(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        account = eth_account["trader"]

        request_params = {
            "account_address_list": [account["account_address"]],
            "include_canceled_items": "test",
        }
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 400
        assert resp.json()["meta"] == {
            "code": 88,
            "description": [
                {
                    "input": "test",
                    "loc": ["query", "include_canceled_items"],
                    "msg": "Input should be a valid boolean, unable to interpret input",
                    "type": "bool_parsing",
                }
            ],
            "message": "Invalid Parameter",
        }

    # Error_3
    # Not supported HTTP method
    def test_error_3(self, client: TestClient, session: Session):
        config.COUPON_TOKEN_ENABLED = True
        resp = client.post(self.apiurl)

        # assertion
        assert resp.status_code == 405
        assert resp.json()["meta"] == {
            "code": 1,
            "message": "Method Not Allowed",
            "description": "method: POST, url: /DEX/OrderList/Coupon",
        }

    # Error_4
    # Coupon token is not enabled
    def test_error_4(self, client: TestClient, session: Session):
        account = eth_account["trader"]

        request_params = {"account_address_list": [account["account_address"]]}
        config.COUPON_TOKEN_ENABLED = False
        resp = client.get(self.apiurl, params=request_params)

        # assertion
        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/OrderList/Coupon",
        }

    # Error_5
    # Exchange address is not set
    def test_error_5(self, client: TestClient, session: Session):
        account = eth_account["trader"]
        request_params = {"account_address_list": [account["account_address"]]}

        config.COUPON_TOKEN_ENABLED = True
        config.IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS = None
        resp = client.get(self.apiurl, params=request_params)

        assert resp.status_code == 404
        assert resp.json()["meta"] == {
            "code": 10,
            "message": "Not Supported",
            "description": "method: GET, url: /DEX/OrderList/Coupon",
        }
