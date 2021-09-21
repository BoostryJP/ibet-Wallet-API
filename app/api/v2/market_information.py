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
from sqlalchemy import func
from sqlalchemy import desc
from sqlalchemy import and_
from cerberus import Validator
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model.db import (
    IDXOrder as Order,
    IDXAgreement as Agreement,
    AgreementStatus
)
from app.errors import (
    InvalidParameterError,
    NotSupportedError
)
from app import config
from app.contracts import Contract

LOG = log.get_logger()


# /Market/Agreement
class GetAgreement(BaseResource):
    """約定情報参照"""

    def on_get(self, req, res):
        LOG.info("v2.market_information.GetAgreement")

        if config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS is None and \
                config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None and \
                config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS is None and \
                config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="GET", url=req.path)

        # 入力値チェック
        request_json = self.validate(req)

        # リクエストから情報を抽出
        order_id = request_json["order_id"]
        agreement_id = request_json["agreement_id"]
        exchange_address = to_checksum_address(request_json["exchange_address"])

        # 取引コントラクトに接続
        address_list = [
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
            config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
        ]
        address_list = [to_checksum_address(address) for address in address_list if address is not None]
        if exchange_address not in address_list:
            raise InvalidParameterError(description="Invalid Address")
        ExchangeContract = Contract.get_contract("IbetExchange", exchange_address)

        # 注文情報の取得
        maker_address, token_address, _, _, is_buy, _, _ = \
            ExchangeContract.functions.getOrder(order_id).call()

        if maker_address == config.ZERO_ADDRESS:
            raise InvalidParameterError("Data not found")

        # 約定情報の取得
        taker_address, amount, price, canceled, paid, expiry = \
            ExchangeContract.functions.getAgreement(order_id, agreement_id).call()

        if taker_address == config.ZERO_ADDRESS:
            raise InvalidParameterError("Data not found")

        if is_buy:
            buyer_address = maker_address
            seller_address = taker_address
        else:
            buyer_address = taker_address
            seller_address = maker_address

        res_data = {
            "token_address": token_address,  # トークンアドレス
            "counterpart": taker_address,  # Takerのアドレス
            "buyer_address": buyer_address,  # 買い手EOA
            "seller_address": seller_address,  # 売り手EOA
            "amount": amount,  # 約定数量
            "price": price,  # 約定単価
            "canceled": canceled,  # 約定取消フラグ
            "paid": paid,  # 支払済フラグ
            "expiry": expiry  # 有効期限（unixtime）
        }

        self.on_success(res, res_data)

    @staticmethod
    def validate(req):
        try:
            request_json = {
                "order_id": int(req.get_param("order_id")),
                "agreement_id": int(req.get_param("agreement_id")),
                "exchange_address": req.get_param("exchange_address")
            }
        except Exception:
            raise InvalidParameterError()

        validator = Validator({
            "order_id": {
                "type": "integer",
                "empty": False,
                "required": True
            },
            "agreement_id": {
                "type": "integer",
                "empty": False,
                "required": True
            },
            "exchange_address": {
                "type": "string",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        try:
            if not Web3.isAddress(request_json["exchange_address"]):
                raise InvalidParameterError
        except:
            raise InvalidParameterError

        return request_json


# /Market/OrderBook/StraightBond
class StraightBondOrderBook(BaseResource):
    """[普通社債]板情報取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.StraightBondOrderBook")
        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False or config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # 入力値チェック
        request_json = StraightBondOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json["token_address"])

        # 注文を抽出
        is_buy = request_json["order_type"] == "buy"  # 相対注文が買い注文かどうか
        exchange_address = to_checksum_address(config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
        # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
        if "account_address" in request_json:
            account_address = to_checksum_address(request_json["account_address"])

            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                #
                # NOTE:DEXでは約定取消時に売注文中状態に戻すため、約定数量には取消分を含めていない
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, and_(Order.unique_order_id == Agreement.unique_order_id,
                                              Agreement.status != AgreementStatus.CANCELED.value)). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                #  5) 指定したアカウントアドレス以外
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
        else:
            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #
                # NOTE:DEXでは約定取消時に売注文中状態に戻すため、約定数量には取消分を含めていない
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, and_(Order.unique_order_id == Agreement.unique_order_id,
                                              Agreement.status != AgreementStatus.CANCELED.value)). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order_id, amount, price, exchange_address,
             account_address, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            if not (agreement_amount is None):
                amount -= int(agreement_amount)
            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue

            order_list_tmp.append({
                "order_id": order_id,
                "price": price,
                "amount": amount,
                "account_address": account_address,
            })

        # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
        if request_json["order_type"] == "buy":
            order_list = sorted(order_list_tmp, key=lambda x: x["price"])
        else:
            order_list = sorted(order_list_tmp, key=lambda x: -x["price"])

        self.on_success(res, order_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address": {
                "type": "string"
            },
            "token_address": {
                "type": "string",
                "empty": False,
                "required": True
            },
            "order_type": {
                "type": "string",
                "empty": False,
                "required": True,
                "allowed": ["buy", "sell"]
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["token_address"]):
            raise InvalidParameterError

        if "account_address" in request_json:
            if not Web3.isAddress(request_json["account_address"]):
                raise InvalidParameterError

        return request_json


# /Market/LastPrice/StraightBond
class StraightBondLastPrice(BaseResource):
    """[普通社債]現在値取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.StraightBondLastPrice")

        if config.BOND_TOKEN_ENABLED is False or config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        request_json = StraightBondLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            "IbetExchange",
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        )

        price_list = []
        for token_address in request_json["address_list"]:
            try:
                last_price = ExchangeContract.functions.lastPrice(
                    to_checksum_address(token_address)).call()
            except Exception as e:
                LOG.error(e)
                last_price = 0
            price_list.append({
                "token_address": token_address,
                "last_price": last_price
            })

        self.on_success(res, price_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json["address_list"]:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


# /v2/Market/Tick/StraightBond
class StraightBondTick(BaseResource):
    """[普通社債]歩み値取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.StraightBondTick")

        if config.BOND_TOKEN_ENABLED is False or config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        request_json = StraightBondTick.validate(req)

        session = req.context["session"]

        tick_list = []
        for token_address in request_json["address_list"]:
            token = to_checksum_address(token_address)
            tick = []
            try:
                entries = session.query(Agreement, Order). \
                    join(Order, Agreement.unique_order_id == Order.unique_order_id). \
                    filter(Order.token_address == token). \
                    filter(Agreement.status == AgreementStatus.DONE.value). \
                    order_by(desc(Agreement.settlement_timestamp)). \
                    all()

                for entry in entries:
                    block_timestamp_utc = entry.IDXAgreement.settlement_timestamp
                    tick.append({
                        "block_timestamp": block_timestamp_utc.strftime("%Y/%m/%d %H:%M:%S"),
                        "buy_address": entry.IDXAgreement.buyer_address,
                        "sell_address": entry.IDXAgreement.seller_address,
                        "order_id": entry.IDXAgreement.order_id,
                        "agreement_id": entry.IDXAgreement.agreement_id,
                        "price": entry.IDXOrder.price,
                        "amount": entry.IDXAgreement.amount
                    })
                tick_list.append({
                    "token_address": token_address,
                    "tick": tick
                })
            except Exception as e:
                LOG.error(e)
                tick_list = []

        self.on_success(res, tick_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json["address_list"]:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


# /v2/Market/OrderBook/Membership
class MembershipOrderBook(BaseResource):
    """[会員権]板情報取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.MembershipOrderBook")
        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # 入力値チェック
        request_json = MembershipOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json["token_address"])

        # 注文を抽出
        is_buy = request_json["order_type"] == "buy"  # 相対注文が買い注文かどうか
        exchange_address = to_checksum_address(config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
        # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
        if "account_address" in request_json:
            account_address = to_checksum_address(request_json["account_address"])

            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                #
                # NOTE:DEXでは約定取消時に売注文中状態に戻すため、約定数量には取消分を含めていない
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, and_(Order.unique_order_id == Agreement.unique_order_id,
                                              Agreement.status != AgreementStatus.CANCELED.value)). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                #  5) 指定したアカウントアドレス以外
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
        else:
            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #
                # NOTE:DEXでは約定取消時に売注文中状態に戻すため、約定数量には取消分を含めていない
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, and_(Order.unique_order_id == Agreement.unique_order_id,
                                              Agreement.status != AgreementStatus.CANCELED.value)). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order_id, amount, price, exchange_address,
             account_address, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            if not (agreement_amount is None):
                amount -= int(agreement_amount)
            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue

            order_list_tmp.append({
                "order_id": order_id,
                "price": price,
                "amount": amount,
                "account_address": account_address,
            })

        # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
        if request_json["order_type"] == "buy":
            order_list = sorted(order_list_tmp, key=lambda x: x["price"])
        else:
            order_list = sorted(order_list_tmp, key=lambda x: -x["price"])

        self.on_success(res, order_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address": {
                "type": "string"
            },
            "token_address": {
                "type": "string",
                "empty": False,
                "required": True
            },
            "order_type": {
                "type": "string",
                "empty": False,
                "required": True,
                "allowed": ["buy", "sell"]
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["token_address"]):
            raise InvalidParameterError

        if "account_address" in request_json:
            if not Web3.isAddress(request_json["account_address"]):
                raise InvalidParameterError

        return request_json


# /v2/Market/LastPrice/Membership
class MembershipLastPrice(BaseResource):
    """[会員権]現在値取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.MembershipLastPrice")

        if config.MEMBERSHIP_TOKEN_ENABLED is False or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        request_json = MembershipLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            "IbetExchange",
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
        )

        price_list = []
        for token_address in request_json["address_list"]:
            try:
                last_price = ExchangeContract.functions. \
                    lastPrice(to_checksum_address(token_address)).call()
            except Exception as e:
                LOG.error(e)
                last_price = 0

            price_list.append({
                "token_address": token_address,
                "last_price": last_price
            })

        self.on_success(res, price_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json["address_list"]:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


# /v2/Market/Tick/Membership
class MembershipTick(BaseResource):
    """[会員権]歩み値取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.MembershipTick")

        if config.MEMBERSHIP_TOKEN_ENABLED is False or config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        request_json = MembershipTick.validate(req)

        session = req.context["session"]

        tick_list = []
        # TokenごとにTickを取得
        for token_address in request_json["address_list"]:
            token = to_checksum_address(token_address)
            tick = []
            try:
                entries = session.query(Agreement, Order). \
                    join(Order, Agreement.unique_order_id == Order.unique_order_id). \
                    filter(Order.token_address == token). \
                    filter(Agreement.status == AgreementStatus.DONE.value). \
                    order_by(desc(Agreement.settlement_timestamp)). \
                    all()

                for entry in entries:
                    block_timestamp_utc = entry.IDXAgreement.settlement_timestamp
                    tick.append({
                        "block_timestamp": block_timestamp_utc.strftime("%Y/%m/%d %H:%M:%S"),
                        "buy_address": entry.IDXAgreement.buyer_address,
                        "sell_address": entry.IDXAgreement.seller_address,
                        "order_id": entry.IDXAgreement.order_id,
                        "agreement_id": entry.IDXAgreement.agreement_id,
                        "price": entry.IDXOrder.price,
                        "amount": entry.IDXAgreement.amount
                    })
                tick_list.append({
                    "token_address": token_address,
                    "tick": tick
                })
            except Exception as e:
                LOG.error(e)
                tick_list = []

        self.on_success(res, tick_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json["address_list"]:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


# /v2/Market/OrderBook/Coupon
class CouponOrderBook(BaseResource):
    """[クーポン]板情報取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.CouponOrderBook")
        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False or config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        # 入力値チェック
        request_json = CouponOrderBook.validate(req)

        # 入力値を抽出
        token_address = to_checksum_address(request_json["token_address"])

        # 注文を抽出
        is_buy = request_json["order_type"] == "buy"  # 相対注文が買い注文かどうか
        exchange_address = to_checksum_address(config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # account_address（注文者のアドレス）指定時は注文者以外の注文板を取得する
        # account_address（注文者のアドレス）未指定時は全ての注文板を取得する
        if "account_address" in request_json:
            account_address = to_checksum_address(request_json["account_address"])

            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #  5) 指定したアカウントアドレス以外
                #
                # NOTE:DEXでは約定取消時に売注文中状態に戻すため、約定数量には取消分を含めていない
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, and_(Order.unique_order_id == Agreement.unique_order_id,
                                              Agreement.status != AgreementStatus.CANCELED.value)). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                #  5) 指定したアカウントアドレス以外
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.account_address != account_address). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
        else:
            if is_buy:  # 買注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以下
                #
                # NOTE:DEXでは約定取消時に売注文中状態に戻すため、約定数量には取消分を含めていない
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, and_(Order.unique_order_id == Agreement.unique_order_id,
                                              Agreement.status != AgreementStatus.CANCELED.value)). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == False). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()
            else:  # 売注文
                # ＜抽出条件＞
                #  1) Token Addressが指定したものと同じ
                #  2) クライアントが買い注文をしたい場合 => 売り注文を抽出
                #               売り注文をしたい場合 => 買い注文を抽出
                #  3) 未キャンセル
                #  4) 指値以上
                orders = session.query(Order.order_id, Order.amount, Order.price, Order.exchange_address,
                                       Order.account_address, func.sum(Agreement.amount)). \
                    outerjoin(Agreement, Order.unique_order_id == Agreement.unique_order_id). \
                    group_by(Order.order_id, Order.amount, Order.price, Order.exchange_address, Order.account_address). \
                    filter(Order.exchange_address == exchange_address). \
                    filter(Order.token_address == token_address). \
                    filter(Order.is_buy == True). \
                    filter(Order.is_cancelled == False). \
                    filter(Order.agent_address == config.AGENT_ADDRESS). \
                    all()

        # レスポンス用の注文一覧を構築
        order_list_tmp = []
        for (order_id, amount, price, exchange_address,
             account_address, agreement_amount) in orders:
            # 残存注文数量 = 発注数量 - 約定済み数量
            if not (agreement_amount is None):
                amount -= int(agreement_amount)
            # 残注文ありの注文のみを抽出する
            if amount <= 0:
                continue

            order_list_tmp.append({
                "order_id": order_id,
                "price": price,
                "amount": amount,
                "account_address": account_address,
            })

        # 買い注文の場合は価格で昇順に、売り注文の場合は価格で降順にソートする
        if request_json["order_type"] == "buy":
            order_list = sorted(order_list_tmp, key=lambda x: x["price"])
        else:
            order_list = sorted(order_list_tmp, key=lambda x: -x["price"])

        self.on_success(res, order_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address": {
                "type": "string"
            },
            "token_address": {
                "type": "string",
                "empty": False,
                "required": True
            },
            "order_type": {
                "type": "string",
                "empty": False,
                "required": True,
                "allowed": ["buy", "sell"]
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["token_address"]):
            raise InvalidParameterError

        if "account_address" in request_json:
            if not Web3.isAddress(request_json["account_address"]):
                raise InvalidParameterError

        return request_json


# /v2/Market/LastPrice/Coupon
class CouponLastPrice(BaseResource):
    """[クーポン]現在値取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.CouponLastPrice")

        if config.COUPON_TOKEN_ENABLED is False or config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        request_json = CouponLastPrice.validate(req)

        ExchangeContract = Contract.get_contract(
            "IbetExchange",
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
        )

        price_list = []
        for token_address in request_json["address_list"]:
            try:
                last_price = ExchangeContract.functions. \
                    lastPrice(to_checksum_address(token_address)).call()
            except Exception as e:
                LOG.error(e)
                last_price = 0

            price_list.append({
                "token_address": token_address,
                "last_price": last_price
            })

        self.on_success(res, price_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json["address_list"]:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json


# /v2/Market/Tick/Coupon
class CouponTick(BaseResource):
    """[クーポン]歩み値取得"""

    def on_post(self, req, res):
        LOG.info("v2.market_information.CouponTick")

        if config.COUPON_TOKEN_ENABLED is False or config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS is None:
            raise NotSupportedError(method="POST", url=req.path)

        request_json = CouponTick.validate(req)

        session = req.context["session"]

        tick_list = []
        # TokenごとにTickを取得
        for token_address in request_json["address_list"]:
            token = to_checksum_address(token_address)
            tick = []
            try:
                entries = session.query(Agreement, Order). \
                    join(Order, Agreement.unique_order_id == Order.unique_order_id). \
                    filter(Order.token_address == token). \
                    filter(Agreement.status == AgreementStatus.DONE.value). \
                    order_by(desc(Agreement.settlement_timestamp)). \
                    all()

                for entry in entries:
                    block_timestamp_utc = entry.IDXAgreement.settlement_timestamp
                    tick.append({
                        "block_timestamp": block_timestamp_utc.strftime("%Y/%m/%d %H:%M:%S"),
                        "buy_address": entry.IDXAgreement.buyer_address,
                        "sell_address": entry.IDXAgreement.seller_address,
                        "order_id": entry.IDXAgreement.order_id,
                        "agreement_id": entry.IDXAgreement.agreement_id,
                        "price": entry.IDXOrder.price,
                        "amount": entry.IDXAgreement.amount
                    })
                tick_list.append({
                    "token_address": token_address,
                    "tick": tick
                })
            except Exception as e:
                LOG.error(e)
                tick_list = []

        self.on_success(res, tick_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "address_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for token_address in request_json["address_list"]:
            if not Web3.isAddress(token_address):
                raise InvalidParameterError

        return request_json
