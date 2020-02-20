# -*- coding: utf-8 -*-
import json
import requests
from datetime import timezone, timedelta

JST = timezone(timedelta(hours=+9), 'JST')

from sqlalchemy import desc

from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Listing, PrivateListing, BondTokenV2, MembershipTokenV2, CouponTokenV2, ConsumeCoupon

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


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

        # Company List：発行体企業リスト
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as e:
            LOG.error(e)
            company_list = []

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
                            name = BondTokenContract.functions.name().call()
                            symbol = BondTokenContract.functions.symbol().call()
                            total_supply = BondTokenContract.functions.totalSupply().call()
                            face_value = BondTokenContract.functions.faceValue().call()
                            interest_rate = BondTokenContract.functions.interestRate().call()

                            interest_payment_date_string = BondTokenContract.functions.interestPaymentDate().call()
                            interest_payment_date1 = ''
                            interest_payment_date2 = ''
                            interest_payment_date3 = ''
                            interest_payment_date4 = ''
                            interest_payment_date5 = ''
                            interest_payment_date6 = ''
                            interest_payment_date7 = ''
                            interest_payment_date8 = ''
                            interest_payment_date9 = ''
                            interest_payment_date10 = ''
                            interest_payment_date11 = ''
                            interest_payment_date12 = ''
                            try:
                                interest_payment_date = json.loads(
                                    interest_payment_date_string.replace(
                                        "'", '"'
                                    ).replace(
                                        'True', 'true'
                                    ).replace(
                                        'False', 'false'
                                    )
                                )
                                if 'interestPaymentDate1' in interest_payment_date:
                                    interest_payment_date1 = interest_payment_date['interestPaymentDate1']
                                if 'interestPaymentDate2' in interest_payment_date:
                                    interest_payment_date2 = interest_payment_date['interestPaymentDate2']
                                if 'interestPaymentDate3' in interest_payment_date:
                                    interest_payment_date3 = interest_payment_date['interestPaymentDate3']
                                if 'interestPaymentDate4' in interest_payment_date:
                                    interest_payment_date4 = interest_payment_date['interestPaymentDate4']
                                if 'interestPaymentDate5' in interest_payment_date:
                                    interest_payment_date5 = interest_payment_date['interestPaymentDate5']
                                if 'interestPaymentDate6' in interest_payment_date:
                                    interest_payment_date6 = interest_payment_date['interestPaymentDate6']
                                if 'interestPaymentDate7' in interest_payment_date:
                                    interest_payment_date7 = interest_payment_date['interestPaymentDate7']
                                if 'interestPaymentDate8' in interest_payment_date:
                                    interest_payment_date8 = interest_payment_date['interestPaymentDate8']
                                if 'interestPaymentDate9' in interest_payment_date:
                                    interest_payment_date9 = interest_payment_date['interestPaymentDate9']
                                if 'interestPaymentDate10' in interest_payment_date:
                                    interest_payment_date10 = interest_payment_date['interestPaymentDate10']
                                if 'interestPaymentDate11' in interest_payment_date:
                                    interest_payment_date11 = interest_payment_date['interestPaymentDate11']
                                if 'interestPaymentDate12' in interest_payment_date:
                                    interest_payment_date12 = interest_payment_date['interestPaymentDate12']
                            except Exception as e:
                                LOG.error(e)
                                pass

                            redemption_date = BondTokenContract.functions.redemptionDate().call()
                            redemption_value = BondTokenContract.functions.redemptionValue().call()
                            return_date = BondTokenContract.functions.returnDate().call()
                            return_amount = BondTokenContract.functions.returnAmount().call()
                            purpose = BondTokenContract.functions.purpose().call()
                            transferable = BondTokenContract.functions.transferable().call()
                            isRedeemed = BondTokenContract.functions.isRedeemed().call()
                            initial_offering_status = BondTokenContract.functions.initialOfferingStatus().call()
                            image_url_1 = BondTokenContract.functions.getImageURL(0).call()
                            image_url_2 = BondTokenContract.functions.getImageURL(1).call()
                            image_url_3 = BondTokenContract.functions.getImageURL(2).call()
                            owner_address = BondTokenContract.functions.owner().call()
                            contact_information = BondTokenContract.functions.contactInformation().call()
                            privacy_policy = BondTokenContract.functions.privacyPolicy().call()

                            company_name, rsa_publickey = \
                                StraightBondMyTokens.get_company_name(company_list, owner_address)

                            # 第三者認定（Sign）のイベント情報を検索する
                            # NOTE:現状項目未使用であるため空のリストを返す
                            certification = []

                            bondtoken = BondTokenV2()
                            bondtoken.token_address = token_address
                            bondtoken.token_template = token_template
                            bondtoken.company_name = company_name
                            bondtoken.rsa_publickey = rsa_publickey
                            bondtoken.name = name
                            bondtoken.symbol = symbol
                            bondtoken.total_supply = total_supply
                            bondtoken.face_value = face_value
                            bondtoken.interest_rate = interest_rate
                            bondtoken.interest_payment_date1 = interest_payment_date1
                            bondtoken.interest_payment_date2 = interest_payment_date2
                            bondtoken.interest_payment_date3 = interest_payment_date3
                            bondtoken.interest_payment_date4 = interest_payment_date4
                            bondtoken.interest_payment_date5 = interest_payment_date5
                            bondtoken.interest_payment_date6 = interest_payment_date6
                            bondtoken.interest_payment_date7 = interest_payment_date7
                            bondtoken.interest_payment_date8 = interest_payment_date8
                            bondtoken.interest_payment_date9 = interest_payment_date9
                            bondtoken.interest_payment_date10 = interest_payment_date10
                            bondtoken.interest_payment_date11 = interest_payment_date11
                            bondtoken.interest_payment_date12 = interest_payment_date12
                            bondtoken.redemption_date = redemption_date
                            bondtoken.redemption_value = redemption_value
                            bondtoken.return_date = return_date
                            bondtoken.return_amount = return_amount
                            bondtoken.purpose = purpose
                            bondtoken.transferable = transferable
                            bondtoken.isRedeemed = isRedeemed
                            bondtoken.image_url = [
                                {'id': 1, 'url': image_url_1},
                                {'id': 2, 'url': image_url_2},
                                {'id': 3, 'url': image_url_3}
                            ]
                            bondtoken.certification = certification
                            bondtoken.initial_offering_status = initial_offering_status
                            bondtoken.max_holding_quantity = token.max_holding_quantity
                            bondtoken.max_sell_amount = token.max_sell_amount
                            bondtoken.payment_method_credit_card = token.payment_method_credit_card
                            bondtoken.payment_method_bank = token.payment_method_bank
                            bondtoken.contact_information = contact_information
                            bondtoken.privacy_policy = privacy_policy

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
    def get_company_name(company_list, owner_address):
        company_name = ''
        rsa_publickey = ''
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']
        return company_name, rsa_publickey

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
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # Company List：発行体企業リスト
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as e:
            LOG.error(e)
            company_list = []

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
                token_info = ListContract.functions. \
                    getTokenByAddress(token.token_address).call()

                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetMembership':
                    TokenContract = Contract. \
                        get_contract('IbetMembership', token_address)
                    try:
                        balance = TokenContract.functions.balanceOf(owner).call()
                        commitment = ExchangeContract.functions. \
                            commitmentOf(owner, token_address).call()

                        # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                        # Note: 現状は、会員権トークンの場合、残高・残注文ゼロの場合は詳細情報を
                        #       返さない仕様としている。
                        if balance == 0 and commitment == 0:
                            continue
                        else:
                            name = TokenContract.functions.name().call()
                            symbol = TokenContract.functions.symbol().call()
                            total_supply = TokenContract.functions.totalSupply().call()
                            details = TokenContract.functions.details().call()
                            return_details = TokenContract.functions.returnDetails().call()
                            expiration_date = TokenContract.functions.expirationDate().call()
                            memo = TokenContract.functions.memo().call()
                            transferable = TokenContract.functions.transferable().call()
                            status = TokenContract.functions.status().call()
                            image_url_1 = TokenContract.functions.getImageURL(0).call()
                            image_url_2 = TokenContract.functions.getImageURL(1).call()
                            image_url_3 = TokenContract.functions.getImageURL(2).call()
                            owner_address = TokenContract.functions.owner().call()
                            contact_information = TokenContract.functions.contactInformation().call()
                            privacy_policy = TokenContract.functions.privacyPolicy().call()

                            company_name, rsa_publickey = MembershipMyTokens. \
                                get_company_name(company_list, owner_address)

                            membershiptoken = MembershipTokenV2()
                            membershiptoken.token_address = token_address
                            membershiptoken.token_template = token_template
                            membershiptoken.owner_address = owner_address
                            membershiptoken.company_name = company_name
                            membershiptoken.rsa_publickey = rsa_publickey
                            membershiptoken.name = name
                            membershiptoken.symbol = symbol
                            membershiptoken.total_supply = total_supply
                            membershiptoken.details = details
                            membershiptoken.return_details = return_details
                            membershiptoken.expiration_date = expiration_date
                            membershiptoken.memo = memo
                            membershiptoken.transferable = transferable
                            membershiptoken.status = status
                            membershiptoken.image_url = [
                                {'id': 1, 'url': image_url_1},
                                {'id': 2, 'url': image_url_2},
                                {'id': 3, 'url': image_url_3}
                            ]
                            membershiptoken.max_holding_quantity = token.max_holding_quantity
                            membershiptoken.max_sell_amount = token.max_sell_amount
                            membershiptoken.payment_method_credit_card = token.payment_method_credit_card
                            membershiptoken.payment_method_bank = token.payment_method_bank
                            membershiptoken.contact_information = contact_information
                            membershiptoken.privacy_policy = privacy_policy

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
    def get_company_name(company_list, owner_address):
        company_name = ''
        rsa_publickey = ''
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']
        return company_name, rsa_publickey

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

        # Company List：発行体企業リスト
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as e:
            LOG.error(e)
            company_list = []

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # Coupon Exchange Contract
        CouponExchangeContract = Contract.get_contract(
            'IbetCouponExchange', config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        listed_tokens = session.query(Listing).all()
        listed_tokens = listed_tokens + session.query(PrivateListing).all()

        position_list = []
        for _account_address in request_json['account_address_list']:
            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in listed_tokens:
                token_info = ListContract.functions. \
                    getTokenByAddress(token.token_address).call()

                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetCoupon':
                    CouponTokenContract = \
                        Contract.get_contract('IbetCoupon', token_address)
                    try:
                        balance = CouponTokenContract.functions.balanceOf(owner).call()
                        commitment = CouponExchangeContract.functions. \
                            commitmentOf(owner, token_address).call()
                        used = CouponTokenContract.functions.usedOf(owner).call()

                        # 残高、残注文、使用済数量がゼロではない場合、詳細情報を取得する
                        if balance == 0 and commitment == 0 and used == 0:
                            continue
                        else:
                            owner_address = CouponTokenContract.functions.owner().call()
                            company_name, rsa_publickey = \
                                CouponMyTokens.get_company_name(company_list, owner_address)
                            name = CouponTokenContract.functions.name().call()
                            symbol = CouponTokenContract.functions.symbol().call()
                            total_supply = CouponTokenContract.functions.totalSupply().call()
                            details = CouponTokenContract.functions.details().call()
                            return_details = CouponTokenContract.functions.returnDetails().call()
                            memo = CouponTokenContract.functions.memo().call()
                            expirationDate = CouponTokenContract.functions.expirationDate().call()
                            transferable = CouponTokenContract.functions.transferable().call()
                            image_url_1 = CouponTokenContract.functions.getImageURL(0).call()
                            image_url_2 = CouponTokenContract.functions.getImageURL(1).call()
                            image_url_3 = CouponTokenContract.functions.getImageURL(2).call()
                            status = CouponTokenContract.functions.status().call()
                            contact_information = CouponTokenContract.functions.contactInformation().call()
                            privacy_policy = CouponTokenContract.functions.privacyPolicy().call()

                            coupontoken = CouponTokenV2()
                            coupontoken.token_address = token_address
                            coupontoken.token_template = token_template
                            coupontoken.owner_address = owner_address
                            coupontoken.company_name = company_name
                            coupontoken.rsa_publickey = rsa_publickey
                            coupontoken.name = name
                            coupontoken.symbol = symbol
                            coupontoken.total_supply = total_supply
                            coupontoken.details = details
                            coupontoken.return_details = return_details
                            coupontoken.memo = memo
                            coupontoken.expiration_date = expirationDate
                            coupontoken.transferable = transferable
                            coupontoken.image_url = [
                                {'id': 1, 'url': image_url_1},
                                {'id': 2, 'url': image_url_2},
                                {'id': 3, 'url': image_url_3}
                            ]
                            coupontoken.status = status
                            coupontoken.max_holding_quantity = token.max_holding_quantity
                            coupontoken.max_sell_amount = token.max_sell_amount
                            coupontoken.payment_method_credit_card = token.payment_method_credit_card
                            coupontoken.payment_method_bank = token.payment_method_bank
                            coupontoken.contact_information = contact_information
                            coupontoken.privacy_policy = privacy_policy

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
    def get_company_name(company_list, owner_address):
        company_name = ''
        rsa_publickey = ''
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']
        return company_name, rsa_publickey

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
        LOG.info('v2.Position.CouponConsumptions')
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

