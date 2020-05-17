# -*- coding: utf-8 -*-
from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, NotSupportedError
from app import config
from app.contracts import Contract
from app.model import Order, Agreement, AgreementStatus, BondToken, MembershipToken, CouponToken, ShareToken
from sqlalchemy import or_

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


class BaseOrderList(object):

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'account_address_list': {
                'type': 'list',
                'schema': {'type': 'string'},
                'empty': False,
                'required': True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json['account_address_list']:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json

    # 注文一覧
    @staticmethod
    def get_OrderList(session, token_model, contract_name, exchange_contract_address, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(exchange_contract_address)
        ExchangeContract = Contract.get_contract(contract_name, exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id, Order.order_timestamp). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id, order_timestamp) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])
                token_detail = token_model.get(session=session, token_address=token_address)
                order_list.append({
                    'token': token_detail.__dict__,
                    'order': {
                        'order_id': order_id,
                        'counterpart_address': '',
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6],
                        'order_timestamp': order_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧
    @staticmethod
    def get_OTC_OrderList(session, token_model, contract_name, exchange_contract_address, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(exchange_contract_address)
        ExchangeContract = Contract.get_contract(contract_name, exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id, Order.order_timestamp). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            # NOTE: 相対取引ではmakerならびに取引対象の注文明細を返却する
            filter(or_(Order.account_address == account_address, Order.counterpart_address == account_address)). \
            all()

        order_list = []
        for (id, order_id, order_timestamp) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[3] != 0:
                token_address = to_checksum_address(orderBook[2])
                token_detail = token_model.get(session=session, token_address=token_address)
                order_list.append({
                    'token': token_detail.__dict__,
                    'order': {
                        'order_id': order_id,
                        'counterpart_address': orderBook[1],
                        'amount': orderBook[3],
                        'price': orderBook[4],
                        'is_buy': False,
                        'canceled': orderBook[6],
                        'order_timestamp': order_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                    },
                    'sort_id': id
                })

        return order_list

    # 決済中一覧
    @staticmethod
    def get_SettlementList(session, token_model, contract_name, exchange_contract_address, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(exchange_contract_address)
        ExchangeContract = Contract.get_contract(contract_name, exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.\
            query(Agreement.id, Agreement.order_id, Agreement.agreement_id, Agreement.agreement_timestamp, Agreement.buyer_address). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(or_(Agreement.buyer_address == account_address, Agreement.seller_address == account_address)). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id, agreement_timestamp, buyer_address) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            token_detail = token_model.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': token_detail.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': buyer_address == account_address,
                    'canceled': agreement[3],
                    'agreement_timestamp': agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧（相対取引買）
    @staticmethod
    def get_OTC_SettlementList(session, token_model, contract_name, exchange_contract_address, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(exchange_contract_address)
        ExchangeContract = Contract.get_contract(contract_name, exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.\
            query(Agreement.id, Agreement.order_id, Agreement.agreement_id, Agreement.agreement_timestamp, Agreement.buyer_address). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(or_(Agreement.buyer_address == account_address, Agreement.seller_address == account_address)). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id, agreement_timestamp, buyer_address) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[2])
            token_detail = token_model.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': token_detail.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': buyer_address == account_address,
                    'canceled': agreement[3],
                    'agreement_timestamp': agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                'sort_id': id
            })

        return settlement_list

    # 約定済一覧
    @staticmethod
    def get_CompleteList(session, token_model, contract_name, exchange_contract_address, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(exchange_contract_address)
        ExchangeContract = Contract.get_contract(contract_name, exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.agreement_timestamp,
            Agreement.settlement_timestamp,
            Agreement.buyer_address). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(or_(Agreement.buyer_address == account_address, Agreement.seller_address == account_address)). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, agreement_timestamp, settlement_timestamp, buyer_address) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            token_detail = token_model.get(session=session, token_address=token_address)
            complete_list.append({
                'token': token_detail.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': buyer_address == account_address,
                    'agreement_timestamp': agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧（相対取引）
    @staticmethod
    def get_OTC_CompleteList(session, token_model, contract_name, exchange_contract_address, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(exchange_contract_address)
        ExchangeContract = Contract.get_contract(contract_name, exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.agreement_timestamp,
            Agreement.settlement_timestamp,
            Agreement.buyer_address). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(or_(Agreement.buyer_address == account_address, Agreement.seller_address == account_address)). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, agreement_timestamp, settlement_timestamp, buyer_address) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[2])
            token_detail = token_model.get(session=session, token_address=token_address)
            complete_list.append({
                'token': token_detail.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': buyer_address == account_address,
                    'agreement_timestamp': agreement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

# ------------------------------
# 注文一覧・約定一覧（普通社債）
# ------------------------------
class StraightBondOrderList(BaseOrderList, BaseResource):
    """
    Handle for endpoint: /v2/OrderList/StraightBond
    """

    def on_post(self, req, res):
        LOG.info('v2.OrderList.StraightBond')
        session = req.context['session']

        # validate
        request_json = self.validate(req)
        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method='POST', url=req.path)

        order_list = []
        settlement_list = []
        complete_list = []
        for account_address in request_json['account_address_list']:
            try:
                # order_list
                order_list.extend(self.get_OrderList(session, BondToken, 'IbetStraightBondExchange', config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS, account_address))
                order_list = sorted(
                    order_list,
                    key=lambda x: x['sort_id']
                )
                # settlement_list
                settlement_list.extend(self.get_SettlementList(session, BondToken, 'IbetStraightBondExchange', config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS, account_address))
                settlement_list = sorted(
                    settlement_list,
                    key=lambda x: x['sort_id']
                )
                # complete_list
                complete_list.extend(self.get_CompleteList(session, BondToken, 'IbetStraightBondExchange', config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS, account_address))
                complete_list = sorted(
                    complete_list,
                    key=lambda x: x['sort_id']
                )
            except Exception as err:
                LOG.error(err)
                pass

        response_json = {
            'order_list': order_list,
            'settlement_list': settlement_list,
            'complete_list': complete_list
        }

        self.on_success(res, response_json)


# ------------------------------
# 注文一覧・約定一覧（会員権）
# ------------------------------
class MembershipOrderList(BaseOrderList, BaseResource):
    """
    Handle for endpoint: /v2/OrderList/Membership
    """

    def on_post(self, req, res):
        LOG.info('v2.OrderList.Membership')
        session = req.context['session']

        # validate
        request_json = self.validate(req)
        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method='POST', url=req.path)

        order_list = []
        settlement_list = []
        complete_list = []

        for account_address in request_json['account_address_list']:
            try:
                # order_list
                order_list.extend(self.get_OrderList(session, MembershipToken, 'IbetMembershipExchange', config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS, account_address))
                order_list = sorted(
                    order_list,
                    key=lambda x: x['sort_id']
                )
                # settlement_list
                settlement_list.extend(self.get_SettlementList(session, MembershipToken, 'IbetMembershipExchange', config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS, account_address))
                settlement_list = sorted(
                    settlement_list,
                    key=lambda x: x['sort_id']
                )
                # complete_list
                complete_list.extend(self.get_CompleteList(session, MembershipToken, 'IbetMembershipExchange', config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS, account_address))
                complete_list = sorted(
                    complete_list,
                    key=lambda x: x['sort_id']
                )
            except Exception as err:
                LOG.error(err)
                pass

        response_json = {
            'order_list': order_list,
            'settlement_list': settlement_list,
            'complete_list': complete_list
        }

        self.on_success(res, response_json)


# ------------------------------
# 注文一覧・約定一覧（クーポン）
# ------------------------------
class CouponOrderList(BaseOrderList, BaseResource):
    """
    Handle for endpoint: /v2/OrderList/Coupon
    """

    def on_post(self, req, res):
        LOG.info('v2.OrderList.Coupon')
        session = req.context['session']

        # validate
        request_json = self.validate(req)
        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method='POST', url=req.path)

        order_list = []
        settlement_list = []
        complete_list = []
        
        for account_address in request_json['account_address_list']:
            try:
                # order_list
                order_list.extend(self.get_OrderList(session, CouponToken, 'IbetCouponExchange', config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS, account_address))
                order_list = sorted(
                    order_list,
                    key=lambda x: x['sort_id']
                )
                # settlement_list
                settlement_list.extend(self.get_SettlementList(session, CouponToken, 'IbetCouponExchange', config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS, account_address))
                settlement_list = sorted(
                    settlement_list,
                    key=lambda x: x['sort_id']
                )
                # complete_list
                complete_list.extend(self.get_CompleteList(session, CouponToken, 'IbetCouponExchange', config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS, account_address))
                complete_list = sorted(
                    complete_list,
                    key=lambda x: x['sort_id']
                )
            except Exception as err:
                LOG.error(err)
                pass

        response_json = {
            'order_list': order_list,
            'settlement_list': settlement_list,
            'complete_list': complete_list
        }

        self.on_success(res, response_json)


# ------------------------------
# 注文一覧・約定一覧（株式）
# ------------------------------
class ShareOrderList(BaseOrderList, BaseResource):
    """
    Handle for endpoint: /v2/OrderList/Share
    """

    def on_post(self, req, res):
        LOG.info('v2.OrderList.Share')
        session = req.context['session']

        # validate
        request_json = self.validate(req)
        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='POST', url=req.path)

        order_list = []
        settlement_list = []
        complete_list = []
        
        for account_address in request_json['account_address_list']:
            try:
                # order_list
                order_list.extend(self.get_OTC_OrderList(session, ShareToken, 'IbetOTCExchange', config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS, account_address))
                order_list = sorted(
                    order_list,
                    key=lambda x: x['sort_id']
                )
                # settlement_list
                settlement_list.extend(self.get_OTC_SettlementList(session, ShareToken, 'IbetOTCExchange', config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS, account_address))
                settlement_list = sorted(
                    settlement_list,
                    key=lambda x: x['sort_id']
                )
                # complete_list
                complete_list.extend(self.get_OTC_CompleteList(session, ShareToken, 'IbetOTCExchange', config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS, account_address))
                complete_list = sorted(
                    complete_list,
                    key=lambda x: x['sort_id']
                )
            except Exception as err:
                LOG.error(err)
                pass

        response_json = {
            'order_list': order_list,
            'settlement_list': settlement_list,
            'complete_list': complete_list
        }

        self.on_success(res, response_json)
