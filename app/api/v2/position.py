# -*- coding: utf-8 -*-
import json
import requests
from datetime import datetime, timezone, timedelta

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
from app.model import Listing, PrivateListing, MembershipToken, CouponToken

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


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

        listed_tokens = session.query(Listing). \
            union(session.query(PrivateListing)). \
            all()

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

                            membershiptoken = MembershipToken()
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
        LOG.info('v1.position.CouponMyTokens')

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

        listed_tokens = session.query(Listing). \
            union(session.query(PrivateListing)). \
            all()

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

                            coupontoken = CouponToken()
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
