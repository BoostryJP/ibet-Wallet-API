# -*- coding: utf-8 -*-
from datetime import timezone, timedelta

JST = timezone(timedelta(hours=+9), 'JST')

from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Listing, PrivateListing, BondToken, ShareToken, MembershipToken, CouponToken, ConsumeCoupon

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# [株式]保有トークン一覧
# ------------------------------
class ShareMyTokens(BaseResource):
    """
    Handle for endpoint: /v2/Position/Share
    """

    def on_post(self, req, res):
        LOG.info('v2.position.ShareMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = ShareMyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetOTCExchange',
            config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
        )

        listed_tokens = session.query(Listing).all()
        listed_tokens = listed_tokens + session.query(PrivateListing).all()

        position_list = []
        for _account_address in request_json['account_address_list']:
            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in listed_tokens:
                token_info = ListContract.functions.getTokenByAddress(token.token_address).call()
                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetShare':
                    TokenContract = Contract.get_contract('IbetShare', token_address)
                    try:
                        balance = TokenContract.functions.balanceOf(owner).call()
                        commitment = ExchangeContract.functions.commitmentOf(owner, token_address).call()
                        # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                        # Note: 現状は、株式トークンの場合、残高・残注文ゼロの場合は詳細情報を
                        #       返さない仕様としている。
                        if balance == 0 and commitment == 0:
                            continue
                        else:
                            sharetoken = ShareToken.get(session=session, token_address=token_address)
                            position_list.append({
                                'token': sharetoken.__dict__,
                                'balance': balance,
                                'commitment': commitment
                            })
                    except Exception as e:
                        LOG.exception(e)
                        continue

        self.on_success(res, position_list)

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


# ------------------------------
# [普通社債]保有トークン一覧
# ------------------------------
class StraightBondMyTokens(BaseResource):
    """
    Handle for endpoint: /v2/Position/StraightBond
    """

    def on_post(self, req, res):
        LOG.info('v2.position.StraightBondMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = StraightBondMyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList',
            config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Bond Exchange Contract
        BondExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange',
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
        )

        listed_tokens = session.query(Listing).all()
        listed_tokens = listed_tokens + session.query(PrivateListing).all()

        position_list = []
        for _account_address in request_json['account_address_list']:
            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in listed_tokens:
                token_info = ListContract.functions.getTokenByAddress(token.token_address).call()
                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetStraightBond':
                    BondTokenContract = Contract.get_contract('IbetStraightBond', token_address)
                    try:
                        balance = BondTokenContract.functions.balanceOf(owner).call()
                        commitment = BondExchangeContract.functions.commitmentOf(owner, token_address).call()

                        # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                        # Note: 現状は、債券トークンの場合、残高・残注文ゼロの場合は詳細情報を
                        #       返さない仕様としている。
                        if balance == 0 and commitment == 0:
                            continue
                        else:
                            bondtoken = BondToken.get(session=session, token_address=token_address)
                            position_list.append({
                                'token': bondtoken.__dict__,
                                'balance': balance,
                                'commitment': commitment
                            })
                    except Exception as e:
                        LOG.error(e)
                        continue

        self.on_success(res, position_list)

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


# ------------------------------
# [会員権]保有トークン一覧
# ------------------------------
class MembershipMyTokens(BaseResource):
    """
    Handle for endpoint: /v2/Position/Membership
    """

    def on_post(self, req, res):
        LOG.info('v2.position.MembershipMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = MembershipMyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList',
            config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange',
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
        )

        listed_tokens = session.query(Listing).all()
        listed_tokens = listed_tokens + session.query(PrivateListing).all()

        position_list = []
        for _account_address in request_json['account_address_list']:
            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in listed_tokens:
                token_info = ListContract.functions.getTokenByAddress(token.token_address).call()
                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetMembership':
                    TokenContract = Contract.get_contract('IbetMembership', token_address)
                    try:
                        balance = TokenContract.functions.balanceOf(owner).call()
                        commitment = ExchangeContract.functions.commitmentOf(owner, token_address).call()

                        # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                        # Note: 現状は、会員権トークンの場合、残高・残注文ゼロの場合は詳細情報を
                        #       返さない仕様としている。
                        if balance == 0 and commitment == 0:
                            continue
                        else:
                            membershiptoken = MembershipToken.get(session=session, token_address=token_address)
                            position_list.append({
                                'token': membershiptoken.__dict__,
                                'balance': balance,
                                'commitment': commitment
                            })
                    except Exception as e:
                        LOG.error(e)
                        continue

        self.on_success(res, position_list)

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


# ------------------------------
# [クーポン]保有トークン一覧
# ------------------------------
class CouponMyTokens(BaseResource):
    """
    Handle for endpoint: /v2/Position/Coupon
    """

    def on_post(self, req, res):
        LOG.info('v2.position.CouponMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = CouponMyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList',
            config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Coupon Exchange Contract
        CouponExchangeContract = Contract.get_contract(
            'IbetCouponExchange',
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
        )

        listed_tokens = session.query(Listing).all()
        listed_tokens = listed_tokens + session.query(PrivateListing).all()

        position_list = []
        for _account_address in request_json['account_address_list']:
            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in listed_tokens:
                token_info = ListContract.functions.getTokenByAddress(token.token_address).call()
                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetCoupon':
                    CouponTokenContract = Contract.get_contract('IbetCoupon', token_address)
                    try:
                        balance = CouponTokenContract.functions.balanceOf(owner).call()
                        commitment = CouponExchangeContract.functions.commitmentOf(owner, token_address).call()
                        used = CouponTokenContract.functions.usedOf(owner).call()

                        # 残高、残注文、使用済数量がゼロではない場合、詳細情報を取得する
                        if balance == 0 and commitment == 0 and used == 0:
                            continue
                        else:
                            coupontoken = CouponToken.get(session=session, token_address=token_address)
                            position_list.append({
                                'token': coupontoken.__dict__,
                                'balance': balance,
                                'commitment': commitment,
                                'used': used
                            })

                    except Exception as e:
                        LOG.error(e)
                        continue

        self.on_success(res, position_list)

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


# ------------------------------
# [クーポン]消費履歴
# ------------------------------
class CouponConsumptions(BaseResource):
    """
    Handle for endpoint: /v2/Position/Coupon/Consumptions
    """

    def on_post(self, req, res):
        LOG.info('v2.position.CouponConsumptions')
        session = req.context['session']

        # 入力値チェック
        request_json = CouponConsumptions.validate(req)

        # クーポン消費履歴のリストを作成
        _coupon_address = to_checksum_address(request_json['token_address'])
        coupon_consumptions = []
        for _account_address in request_json['account_address_list']:
            consumptions = session.query(ConsumeCoupon).\
                filter(ConsumeCoupon.token_address == _coupon_address).\
                filter(ConsumeCoupon.account_address == _account_address).\
                all()
            for consumption in consumptions:
                coupon_consumptions.append({
                    'account_address': _account_address,
                    'block_timestamp': consumption.block_timestamp.strftime('%Y/%m/%d %H:%M:%S'),
                    'value': consumption.amount
                })

        # block_timestampの昇順にソートする
        # Note: もともとのリストはaccountのリストでループして作成したリストなので、古い順になっていないため
        coupon_consumptions = sorted(
            coupon_consumptions,
            key=lambda x: x['block_timestamp']
        )

        self.on_success(res, coupon_consumptions)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'token_address': {
                'type': 'string',
                'empty': False,
                'required': True
            },
            'account_address_list': {
                'type': 'list',
                'schema': {'type': 'string'},
                'empty': False,
                'required': True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json['token_address']):
            raise InvalidParameterError

        for account_address in request_json['account_address_list']:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json
