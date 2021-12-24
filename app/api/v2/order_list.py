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
from cerberus import Validator
from sqlalchemy import or_
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    NotSupportedError
)
from app import config
from app.contracts import Contract
from app.model.db import (
    IDXOrder as Order,
    IDXAgreement as Agreement,
    AgreementStatus
)
from app.model.blockchain import (
    BondToken,
    MembershipToken,
    CouponToken,
    ShareToken
)

LOG = log.get_logger()


class BaseOrderList(object):

    @staticmethod
    def get_order_list(
            session,
            token_model,
            exchange_contract_address,
            account_address,
            include_canceled_items
    ):
        """List all orders from the account (DEX)"""
        # Get exchange contract
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = Contract.get_contract("IbetExchange", exchange_address)

        # Filter order events that are generated from account_address
        query = session.query(
                Order.id,
                Order.order_id,
                Order.order_timestamp
            ). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.account_address == account_address)

        if include_canceled_items is not None and include_canceled_items is True:
            _order_events = query.all()
        else:  # default
            _order_events = query.filter(Order.is_cancelled == False).all()

        order_list = []
        for (id, order_id, order_timestamp) in _order_events:
            order_book = Contract.call_function(
                contract=exchange_contract,
                function_name="getOrder",
                args=(order_id,),
            )
            # If there are no remaining orders, skip this process
            if order_book[2] != 0:
                _order = {
                    "order": {
                        "order_id": order_id,
                        "counterpart_address": "",
                        "amount": order_book[2],
                        "price": order_book[3],
                        "is_buy": order_book[4],
                        "canceled": order_book[6],
                        "order_timestamp": order_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                    },
                    "sort_id": id
                }
                if token_model is not None:
                    token_detail = token_model.get(
                        session=session,
                        token_address=to_checksum_address(order_book[1])
                    )
                    _order["token"] = token_detail.__dict__

                order_list.append(_order)

        return order_list

    @staticmethod
    def get_settlement_list(
            session,
            token_model,
            exchange_contract_address,
            account_address
    ):
        """List all orders in process of settlement (DEX)"""
        # Get exchange contract
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = Contract.get_contract("IbetExchange", exchange_address)

        # Filter agreement events (settlement not completed) generated from account_address
        _agreement_events = session.query(
                Agreement.id,
                Agreement.order_id,
                Agreement.agreement_id,
                Agreement.agreement_timestamp,
                Agreement.buyer_address
            ). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(or_(
                Agreement.buyer_address == account_address,
                Agreement.seller_address == account_address
            )). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id, agreement_timestamp, buyer_address) in _agreement_events:
            order_book = Contract.call_function(
                contract=exchange_contract,
                function_name="getOrder",
                args=(order_id,),
            )
            agreement = Contract.call_function(
                contract=exchange_contract,
                function_name="getAgreement",
                args=(order_id, agreement_id, ),
            )
            _settlement = {
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                "sort_id": id
            }
            if token_model is not None:
                token_detail = token_model.get(
                    session=session,
                    token_address=to_checksum_address(order_book[1])
                )
                _settlement["token"] = token_detail.__dict__

            settlement_list.append(_settlement)

        return settlement_list

    @staticmethod
    def get_complete_list(
            session,
            token_model,
            exchange_contract_address,
            account_address,
            include_canceled_items
    ):
        """List all orders that have been settled (DEX)"""
        # Get exchange contract
        exchange_address = to_checksum_address(exchange_contract_address)
        exchange_contract = Contract.get_contract("IbetExchange", exchange_address)

        # Filter agreement events (settlement completed) generated from account_address
        query = session.query(
                Agreement.id,
                Agreement.order_id,
                Agreement.agreement_id,
                Agreement.agreement_timestamp,
                Agreement.settlement_timestamp,
                Agreement.buyer_address
            ). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(or_(
                Agreement.buyer_address == account_address,
                Agreement.seller_address == account_address
            ))

        if include_canceled_items is not None and include_canceled_items is True:
            _agreement_events = query. \
                filter(or_(
                    Agreement.status == AgreementStatus.DONE.value,
                    Agreement.status == AgreementStatus.CANCELED.value
                )). \
                all()
        else:  # default
            _agreement_events = query. \
                filter(Agreement.status == AgreementStatus.DONE.value). \
                all()

        complete_list = []
        for (id, order_id, agreement_id, agreement_timestamp, settlement_timestamp, buyer_address) in _agreement_events:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ""
            order_book = Contract.call_function(
                contract=exchange_contract,
                function_name="getOrder",
                args=(order_id,),
            )
            agreement = Contract.call_function(
                contract=exchange_contract,
                function_name="getAgreement",
                args=(order_id, agreement_id,),
            )
            _complete = {
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                "settlement_timestamp": settlement_timestamp_jp,
                "sort_id": id
            }
            if token_model is not None:
                token_detail = token_model.get(
                    session=session,
                    token_address=to_checksum_address(order_book[1])
                )
                _complete["token"] = token_detail.__dict__

            complete_list.append(_complete)

        return complete_list

    @staticmethod
    def get_order_list_filtered_by_token(
            session,
            token_address,
            account_address,
            include_canceled_items
    ):
        """List orders from accounts filtered by token address (DEX)"""

        # Filter order events that are generated from account_address
        query = session.query(
                Order.id,
                Order.exchange_address,
                Order.order_id,
                Order.order_timestamp
            ). \
            filter(Order.token_address == token_address). \
            filter(Order.account_address == account_address)

        if include_canceled_items is not None and include_canceled_items is True:
            _order_events = query.all()
        else:  # default
            _order_events = query.filter(Order.is_cancelled == False).all()

        order_list = []
        for (id, exchange_contract_address, order_id, order_timestamp) in _order_events:
            exchange_contract = Contract.get_contract(
                contract_name="IbetExchange",
                address=exchange_contract_address
            )
            order_book = Contract.call_function(
                contract=exchange_contract,
                function_name="getOrder",
                args=(order_id,),
            )
            # If there are no remaining orders, skip this process
            if order_book[2] != 0:
                _order = {
                    "token": {
                        "token_address": token_address
                    },
                    "order": {
                        "order_id": order_id,
                        "counterpart_address": "",
                        "amount": order_book[2],
                        "price": order_book[3],
                        "is_buy": order_book[4],
                        "canceled": order_book[6],
                        "order_timestamp": order_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                    },
                    "sort_id": id
                }
                order_list.append(_order)

        return order_list

    @staticmethod
    def get_settlement_list_filtered_by_token(
            session,
            token_address,
            account_address
    ):
        """List all orders in process of settlement (DEX)"""

        # Filter agreement events (settlement not completed) generated from account_address
        _agreement_events = session.query(
                Agreement.id,
                Agreement.exchange_address,
                Agreement.order_id,
                Agreement.agreement_id,
                Agreement.agreement_timestamp,
                Agreement.buyer_address
            ). \
            outerjoin(Order, Agreement.unique_order_id == Order.unique_order_id). \
            filter(Order.token_address == token_address). \
            filter(or_(
                Agreement.buyer_address == account_address,
                Agreement.seller_address == account_address
            )). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, exchange_contract_address, order_id, agreement_id, agreement_timestamp, buyer_address) in _agreement_events:
            exchange_contract = Contract.get_contract(
                contract_name="IbetExchange",
                address=exchange_contract_address
            )
            agreement = Contract.call_function(
                contract=exchange_contract,
                function_name="getAgreement",
                args=(order_id, agreement_id,),
            )
            _settlement = {
                "token": {
                    "token_address": token_address
                },
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                "sort_id": id
            }
            settlement_list.append(_settlement)

        return settlement_list

    @staticmethod
    def get_complete_list_filtered_by_token(
            session,
            token_address,
            account_address,
            include_canceled_items
    ):
        """List all orders that have been settled (DEX)"""

        # Filter agreement events (settlement completed) generated from account_address
        query = session.query(
                Agreement.id,
                Agreement.exchange_address,
                Agreement.order_id,
                Agreement.agreement_id,
                Agreement.agreement_timestamp,
                Agreement.settlement_timestamp,
                Agreement.buyer_address
            ). \
            outerjoin(Order, Agreement.unique_order_id == Order.unique_order_id). \
            filter(or_(
                Agreement.buyer_address == account_address,
                Agreement.seller_address == account_address
            )). \
            filter(Order.token_address == token_address)

        if include_canceled_items is not None and include_canceled_items is True:
            _agreement_events = query. \
                filter(or_(
                    Agreement.status == AgreementStatus.DONE.value,
                    Agreement.status == AgreementStatus.CANCELED.value
                )). \
                all()
        else:  # default
            _agreement_events = query. \
                filter(Agreement.status == AgreementStatus.DONE.value). \
                all()

        complete_list = []
        for (id, exchange_contract_address, order_id, agreement_id, agreement_timestamp, settlement_timestamp, buyer_address) in _agreement_events:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ""
            exchange_contract = Contract.get_contract(
                contract_name="IbetExchange",
                address=exchange_contract_address
            )
            agreement = Contract.call_function(
                contract=exchange_contract,
                function_name="getAgreement",
                args=(order_id, agreement_id,),
            )
            _complete = {
                "token": {
                    "token_address": token_address
                },
                "agreement": {
                    "exchange_address": exchange_contract_address,
                    "order_id": order_id,
                    "agreement_id": agreement_id,
                    "amount": agreement[1],
                    "price": agreement[2],
                    "is_buy": buyer_address == account_address,
                    "canceled": agreement[3],
                    "agreement_timestamp": agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                "settlement_timestamp": settlement_timestamp_jp,
                "sort_id": id
            }
            complete_list.append(_complete)

        return complete_list


# ------------------------------
# 注文一覧・約定一覧
# ------------------------------
class OrderList(BaseOrderList, BaseResource):
    """
    Endpoint: /v2/OrderList/{token_address}
    """

    def on_post(self, req, res, token_address: str = None, **kwargs):
        LOG.info("v2.order_list.OrderList")
        session = req.context["session"]

        # path validation
        try:
            token_address = to_checksum_address(token_address)
            if not Web3.isAddress(token_address):
                description = "invalid token_address"
                raise InvalidParameterError(description=description)
        except:
            description = "invalid token_address"
            raise InvalidParameterError(description=description)

        # input validate
        request_json = self.validate(req)

        order_list = []
        settlement_list = []
        complete_list = []
        for account_address in request_json["account_address_list"]:
            try:
                # order_list
                order_list.extend(
                    self.get_order_list_filtered_by_token(
                        session=session,
                        token_address=token_address,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    self.get_settlement_list_filtered_by_token(
                        session=session,
                        token_address=token_address,
                        account_address=account_address
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    self.get_complete_list_filtered_by_token(
                        session=session,
                        token_address=token_address,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            },
            "include_canceled_items": {
                "type": "boolean",
                "required": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError("invalid account address")

        return request_json


# ------------------------------
# 注文一覧・約定一覧（普通社債）
# ------------------------------
class StraightBondOrderList(BaseOrderList, BaseResource):
    """
    Endpoint: /v2/OrderList/StraightBond
    """

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.order_list.StraightBondOrderList")
        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False or config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # validate
        request_json = self.validate(req)

        order_list = []
        settlement_list = []
        complete_list = []
        for account_address in request_json["account_address_list"]:
            try:
                # order_list
                order_list.extend(
                    self.get_order_list(
                        session=session,
                        token_model=BondToken,
                        exchange_contract_address=config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    self.get_settlement_list(
                        session=session,
                        token_model=BondToken,
                        exchange_contract_address=config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    self.get_complete_list(
                        session=session,
                        token_model=BondToken,
                        exchange_contract_address=config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            },
            "include_canceled_items": {
                "type": "boolean",
                "required": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json


# ------------------------------
# 注文一覧・約定一覧（会員権）
# ------------------------------
class MembershipOrderList(BaseOrderList, BaseResource):
    """
    Endpoint: /v2/OrderList/Membership
    """

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.order_list.MembershipOrderList")
        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # validate
        request_json = self.validate(req)

        order_list = []
        settlement_list = []
        complete_list = []

        for account_address in request_json["account_address_list"]:
            try:
                # order_list
                order_list.extend(
                    self.get_order_list(
                        session=session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    self.get_settlement_list(
                        session=session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    self.get_complete_list(
                        session=session,
                        token_model=MembershipToken,
                        exchange_contract_address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            },
            "include_canceled_items": {
                "type": "boolean",
                "required": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json


# ------------------------------
# 注文一覧・約定一覧（クーポン）
# ------------------------------
class CouponOrderList(BaseOrderList, BaseResource):
    """
    Endpoint: /v2/OrderList/Coupon
    """

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.order_list.CouponOrderList")
        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False or config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # validate
        request_json = self.validate(req)

        order_list = []
        settlement_list = []
        complete_list = []

        for account_address in request_json["account_address_list"]:
            try:
                # order_list
                order_list.extend(
                    self.get_order_list(
                        session=session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    self.get_settlement_list(
                        session=session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    self.get_complete_list(
                        session=session,
                        token_model=CouponToken,
                        exchange_contract_address=config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            },
            "include_canceled_items": {
                "type": "boolean",
                "required": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json


# ------------------------------
# 注文一覧・約定一覧（株式）
# ------------------------------
class ShareOrderList(BaseOrderList, BaseResource):
    """
    Endpoint: /v2/OrderList/Share
    """

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.order_list.ShareOrderList")
        session = req.context["session"]

        if config.SHARE_TOKEN_ENABLED is False or config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # validate
        request_json = self.validate(req)

        order_list = []
        settlement_list = []
        complete_list = []

        for account_address in request_json["account_address_list"]:
            try:
                # order_list
                order_list.extend(
                    self.get_order_list(
                        session=session,
                        token_model=ShareToken,
                        exchange_contract_address=config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                order_list = sorted(order_list, key=lambda x: x["sort_id"])

                # settlement_list
                settlement_list.extend(
                    self.get_settlement_list(
                        session=session,
                        token_model=ShareToken,
                        exchange_contract_address=config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address
                    )
                )
                settlement_list = sorted(settlement_list, key=lambda x: x["sort_id"])

                # complete_list
                complete_list.extend(
                    self.get_complete_list(
                        session=session,
                        token_model=ShareToken,
                        exchange_contract_address=config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
                        account_address=account_address,
                        include_canceled_items=request_json.get("include_canceled_items")
                    )
                )
                complete_list = sorted(complete_list, key=lambda x: x["sort_id"])
            except Exception as err:
                LOG.exception(err)

        response_json = {
            "order_list": order_list,
            "settlement_list": settlement_list,
            "complete_list": complete_list
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            },
            "include_canceled_items": {
                "type": "boolean",
                "required": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json
