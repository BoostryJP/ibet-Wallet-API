# -*- coding: utf-8 -*-
from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Order, Agreement, AgreementStatus, BondToken, MembershipToken, CouponToken

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# 注文一覧・約定一覧
# ------------------------------
class OrderList(BaseResource):
    """
    Handle for endpoint: /v2/OrderList/
    """

    def on_post(self, req, res):
        LOG.info('v2.OrderList.OrderList')
        session = req.context['session']

        request_json = OrderList.validate(req)

        '''
        1) 注文一覧（order_list）
        '''
        order_list = []
        for account_address in request_json['account_address_list']:
            # BOND
            if config.BOND_TOKEN_ENABLED is True:
                try:
                    order_list.extend(OrderList.get_StraightBond_OrderList(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            # MEMBERSHIP
            if config.MEMBERSHIP_TOKEN_ENABLED is True:
                try:
                    order_list.extend(OrderList.get_Membership_OrderList(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            # COUPON
            if config.COUPON_TOKEN_ENABLED is True:
                try:
                    order_list.extend(OrderList.get_Coupon_OrderList(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            order_list = sorted(
                order_list,
                key=lambda x: x['sort_id']
            )

        '''
        2) 決済中一覧（settlement_list）
        '''
        settlement_list = []
        for account_address in request_json['account_address_list']:
            # BOND
            if config.BOND_TOKEN_ENABLED is True:
                # BOND_BUY
                try:
                    settlement_list.extend(OrderList.get_StraightBond_SettlementList_Buy(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass
                # BOND_SELL
                try:
                    settlement_list.extend(OrderList.get_StraightBond_SettlementList_Sell(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            # MEMBERSHIP
            if config.MEMBERSHIP_TOKEN_ENABLED is True:
                # MEMBERSHIP_BUY
                try:
                    settlement_list.extend(OrderList.get_Membership_SettlementList_Buy(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass
                # MEMBERSHIP_SELL
                try:
                    settlement_list.extend(OrderList.get_Membership_SettlementList_Sell(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            # COUPON
            if config.COUPON_TOKEN_ENABLED is True:
                # COUPON_BUY
                try:
                    settlement_list.extend(OrderList.get_Coupon_SettlementList_Buy(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass
                # COUPON_SELL
                try:
                    settlement_list.extend(OrderList.get_Coupon_SettlementList_Sell(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            settlement_list = sorted(
                settlement_list,
                key=lambda x: x['sort_id']
            )

        '''
        3) 約定済一覧（complete_list）
        '''
        complete_list = []
        for account_address in request_json['account_address_list']:
            # BOND
            if config.BOND_TOKEN_ENABLED is True:
                # BOND_BUY
                try:
                    complete_list.extend(OrderList.get_StraightBond_CompleteList_Buy(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass
                # BOND_SELL
                try:
                    complete_list.extend(OrderList.get_StraightBond_CompleteList_Sell(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            # MEMBERSHIP
            if config.MEMBERSHIP_TOKEN_ENABLED is True:
                # MEMBERSHIP_BUY
                try:
                    complete_list.extend(OrderList.get_Membership_CompleteList_Buy(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass
                # MEMBERSHIP_SELL
                try:
                    complete_list.extend(OrderList.get_Membership_CompleteList_Sell(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            # COUPON
            if config.COUPON_TOKEN_ENABLED is True:
                # COUPON_BUY
                try:
                    complete_list.extend(OrderList.get_Coupon_CompleteList_Buy(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass
                # COUPON_SELL
                try:
                    complete_list.extend(OrderList.get_Coupon_CompleteList_Sell(session, account_address))
                except Exception as err:
                    LOG.error(err)
                    pass

            complete_list = sorted(
                complete_list,
                key=lambda x: x['sort_id']
            )

        response_json = {
            'order_list': order_list,
            'settlement_list': settlement_list,
            'complete_list': complete_list
        }

        self.on_success(res, response_json)

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

    # 注文一覧：普通社債トークン
    @staticmethod
    def get_StraightBond_OrderList(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])
                bondtoken = BondToken.get(session=session, token_address=token_address)
                order_list.append({
                    'token': bondtoken.__dict__,
                    'order': {
                        'order_id': order_id,
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧：会員権トークン
    @staticmethod
    def get_Membership_OrderList(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])
                membershiptoken = MembershipToken.get(session=session, token_address=token_address)
                order_list.append({
                    'token': membershiptoken.__dict__,
                    'order': {
                        'order_id': order_id,
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧：クーポントークン
    @staticmethod
    def get_Coupon_OrderList(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])
                coupontoken = CouponToken.get(session=session, token_address=token_address)
                order_list.append({
                    'token': coupontoken.__dict__,
                    'order': {
                        'order_id': order_id,
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 決済中一覧：普通社債トークン（買）
    @staticmethod
    def get_StraightBond_SettlementList_Buy(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            bondtoken = BondToken.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：普通社債トークン（売）
    @staticmethod
    def get_StraightBond_SettlementList_Sell(session, account_address):
        exchange_address = to_checksum_address(
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            bondtoken = BondToken.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：会員権トークン（買）
    @staticmethod
    def get_Membership_SettlementList_Buy(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            membershiptoken = MembershipToken.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：会員権トークン（売）
    @staticmethod
    def get_Membership_SettlementList_Sell(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            membershiptoken = MembershipToken.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：クーポントークン（買）
    @staticmethod
    def get_Coupon_SettlementList_Buy(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            coupontoken = CouponToken.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：クーポントークン（売）
    @staticmethod
    def get_Coupon_SettlementList_Sell(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            coupontoken = CouponToken.get(session=session, token_address=token_address)
            settlement_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 約定済一覧：普通社債トークン（買）
    @staticmethod
    def get_StraightBond_CompleteList_Buy(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            bondtoken = BondToken.get(session=session, token_address=token_address)
            complete_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：普通社債トークン（売）
    @staticmethod
    def get_StraightBond_CompleteList_Sell(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            bondtoken = BondToken.get(session=session, token_address=token_address)
            complete_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：会員権トークン（買）
    @staticmethod
    def get_Membership_CompleteList_Buy(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            membershiptoken = MembershipToken.get(session=session, token_address=token_address)
            complete_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：会員権トークン（売）
    @staticmethod
    def get_Membership_CompleteList_Sell(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            membershiptoken = MembershipToken.get(session=session, token_address=token_address)
            complete_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：クーポントークン（買）
    @staticmethod
    def get_Coupon_CompleteList_Buy(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            coupontoken = CouponToken.get(session=session, token_address=token_address)
            complete_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：クーポントークン（売）
    @staticmethod
    def get_Coupon_CompleteList_Sell(session, account_address):
        # Exchange Contract
        exchange_address = to_checksum_address(config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)
        ExchangeContract = Contract.get_contract('IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp.strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])
            coupontoken = CouponToken.get(session=session, token_address=token_address)
            complete_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list
