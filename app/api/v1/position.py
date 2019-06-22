# -*- coding: utf-8 -*-
import json
import requests
import os
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
from app.model import Listing, PrivateListing, BondToken, MembershipToken, CouponToken, MRFToken, JDRToken

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# [普通社債]保有トークン一覧
# ------------------------------
class MyTokens(BaseResource):
    """
    Handle for endpoint: /v1/MyTokens/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.MyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = MyTokens.validate(req)

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

        # Bond Exchange Contract
        BondExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        listed_tokens = session.query(Listing).\
            union(session.query(PrivateListing)).\
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

                if token_template == 'IbetStraightBond':
                    BondTokenContract = Contract. \
                        get_contract('IbetStraightBond', token_address)
                    try:
                        balance = BondTokenContract.functions.balanceOf(owner).call()
                        commitment = BondExchangeContract.functions. \
                            commitmentOf(owner, token_address).call()

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

                            interest_payment_date_string = \
                                BondTokenContract.functions.interestPaymentDate().call()
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
                            redemption_amount = BondTokenContract.functions.redemptionAmount().call()
                            return_date = BondTokenContract.functions.returnDate().call()
                            return_amount = BondTokenContract.functions.returnAmount().call()
                            purpose = BondTokenContract.functions.purpose().call()
                            image_url_1 = BondTokenContract.functions.getImageURL(0).call()
                            image_url_2 = BondTokenContract.functions.getImageURL(1).call()
                            image_url_3 = BondTokenContract.functions.getImageURL(2).call()
                            owner_address = BondTokenContract.functions.owner().call()
                            contact_information = BondTokenContract.functions.contactInformation().call()
                            privacy_policy = BondTokenContract.functions.privacyPolicy().call()

                            company_name, rsa_publickey = \
                                MyTokens.get_company_name(company_list, owner_address)

                            # 第三者認定（Sign）のイベント情報を検索する
                            # NOTE:現状項目未使用であるため空のリストを返す
                            certification = []

                            bondtoken = BondToken()
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
                            bondtoken.redemption_amount = redemption_amount
                            bondtoken.return_date = return_date
                            bondtoken.return_amount = return_amount
                            bondtoken.purpose = purpose
                            bondtoken.image_url = [
                                {'id': 1, 'url': image_url_1},
                                {'id': 2, 'url': image_url_2},
                                {'id': 3, 'url': image_url_3}
                            ]
                            bondtoken.certification = certification
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
    Handle for endpoint: /v1/Membership/MyTokens/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.MembershipMyTokens')

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
    Handle for endpoint: /v1/Coupon/MyTokens/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.CouponMyTokens')

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


# ------------------------------
# [クーポン]消費履歴
# ------------------------------
class CouponConsumptions(BaseResource):
    """
    Handle for endpoint: /v1/CouponConsumptions/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.CouponConsumptions')
        request_json = CouponConsumptions.validate(req)

        # Coupon Exchange Contract
        _coupon_address = to_checksum_address(request_json['token_address'])
        CouponContract = Contract.get_contract('IbetCoupon', _coupon_address)

        # クーポン消費履歴のリストを作成
        coupon_consumptions = []
        for _account_address in request_json['account_address_list']:

            # イベント抽出：IbetCoupon（トークン消費イベント）
            # _account_address と consumer が一致するイベントを抽出する。
            try:
                event_filter = CouponContract.events.Consume.createFilter(
                    fromBlock='earliest',
                    argument_filters={
                        'consumer': to_checksum_address(_account_address)
                    }
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    coupon_consumptions.append({
                        'account_address': _account_address,
                        'block_timestamp': datetime.fromtimestamp(
                            web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST
                        ).strftime("%Y/%m/%d %H:%M:%S"),
                        'value': entry['args']['value']
                    })
            except Exception as e:
                LOG.error(e)
                pass

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


# ------------------------------
# [MRF]保有トークン一覧
# ------------------------------
class MRFMyTokens(BaseResource):
    """
    Handle for endpoint: /v1/MRF/MyTokens/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.MRFMyTokens')

        # 入力値チェック
        request_json = MRFMyTokens.validate(req)

        # 企業リスト取得
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as e:
            LOG.error(e)
            company_list = []

        position_list = []
        for account_address in request_json['account_address_list']:
            account_address = to_checksum_address(account_address)

            # MRFトークン設定
            TokenContract = Contract.get_contract(
                'IbetMRF',
                config.IBET_MRF_TOKEN_ADDRESS
            )

            try:
                balance = TokenContract.functions.balanceOf(account_address).call()
                # 残高がゼロではない場合、詳細情報を取得する
                if balance == 0:
                    continue
                else:
                    owner_address = TokenContract.functions.owner().call()
                    company_name, rsa_publickey = \
                        CouponMyTokens.get_company_name(company_list, owner_address)
                    name = TokenContract.functions.name().call()
                    symbol = TokenContract.functions.symbol().call()
                    total_supply = TokenContract.functions.totalSupply().call()
                    details = TokenContract.functions.details().call()
                    memo = TokenContract.functions.memo().call()
                    image_url_1 = TokenContract.functions.getImageURL(0).call()
                    image_url_2 = TokenContract.functions.getImageURL(1).call()
                    image_url_3 = TokenContract.functions.getImageURL(2).call()
                    status = TokenContract.functions.status().call()
                    contact_information = TokenContract.functions.contactInformation().call()
                    privacy_policy = TokenContract.functions.privacyPolicy().call()

                    token = MRFToken()
                    token.token_address = config.IBET_MRF_TOKEN_ADDRESS
                    token.token_template = 'IbetMRF'
                    token.owner_address = owner_address
                    token.company_name = company_name
                    token.rsa_publickey = rsa_publickey
                    token.name = name
                    token.symbol = symbol
                    token.total_supply = total_supply
                    token.details = details
                    token.memo = memo
                    token.image_url = [
                        {'id': 1, 'url': image_url_1},
                        {'id': 2, 'url': image_url_2},
                        {'id': 3, 'url': image_url_3}
                    ]
                    token.status = status
                    token.contact_information = contact_information
                    token.privacy_policy = privacy_policy

                    position_list.append({
                        'token': token.__dict__,
                        'balance': balance,
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
# [MRF]送受信履歴
# ------------------------------
class MRFTransfers(BaseResource):
    """
    Handle for endpoint: /v1/MRF/Transfers/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.MRFTransfers')
        request_json = MRFTransfers.validate(req)

        # MRF Contract との接続
        MRFContract = Contract.get_contract(
            'IbetMRF',
            to_checksum_address(request_json['token_address'])
        )

        # 送受信履歴のリストを作成
        mrf_transfers = []
        for account_address in request_json['account_address_list']:

            # イベント抽出
            # コントラクト：IbetMRF
            # イベント：Transfer（振替）
            try:
                # 送信（used_type="out"）
                # 抽出条件：from が account_address と一致
                event_filter = MRFContract.events.Transfer.createFilter(
                    fromBlock='earliest',
                    argument_filters={
                        'from': to_checksum_address(account_address)
                    }
                )
                entries = event_filter.get_all_entries()

                for entry in entries:
                    mrf_transfers.append({
                        'account_address': account_address,
                        'block_timestamp': datetime.fromtimestamp(
                            web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST
                        ).strftime("%Y/%m/%d %H:%M:%S"),
                        'value': entry['args']['value'],
                        'used_type': 'out'
                    })

                web3.eth.uninstallFilter(event_filter.filter_id)

                # 受信（used_type="in"）
                # 抽出条件：to が account_address と一致
                event_filter = MRFContract.events.Transfer.createFilter(
                    fromBlock='earliest',
                    argument_filters={
                        'to': to_checksum_address(account_address)
                    }
                )
                entries = event_filter.get_all_entries()

                for entry in entries:
                    mrf_transfers.append({
                        'account_address': account_address,
                        'block_timestamp': datetime.fromtimestamp(
                            web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST
                        ).strftime("%Y/%m/%d %H:%M:%S"),
                        'value': entry['args']['value'],
                        'used_type': 'in'
                    })

                web3.eth.uninstallFilter(event_filter.filter_id)

            except Exception as e:
                LOG.error(e)
                pass

        # block_timestampの昇順にソートしなおす
        mrf_transfers = sorted(
            mrf_transfers,
            key=lambda x: x['block_timestamp']
        )

        self.on_success(res, mrf_transfers)

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


# ------------------------------
# [JDR]保有トークン一覧
# ------------------------------
class JDRMyTokens(BaseResource):
    """
    Handle for endpoint: /v1/JDR/MyTokens/
    """

    def on_post(self, req, res):
        LOG.info('v1.Position.JDRMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = JDRMyTokens.validate(req)

        # 企業リスト取得
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as e:
            LOG.error(e)
            company_list = []

        # TokenList コントラクト設定
        ListContract = Contract.get_contract(
            'TokenList',
            config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        listed_tokens = session.query(Listing). \
            union(session.query(PrivateListing)). \
            all()

        position_list = []
        for _account_address in request_json['account_address_list']:
            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in listed_tokens:
                # TokenListコントラクトの登録情報を取得
                token_info = ListContract.functions.getTokenByAddress(token.token_address).call()
                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)  # トークン保有者

                # token_templateがIbetDepositaryReceiptであるものに対して詳細情報を取得する
                if token_template == 'IbetDepositaryReceipt':
                    TokenContract = Contract.get_contract(
                        'IbetDepositaryReceipt',
                        token_address
                    )
                    try:
                        # 残高取得
                        balance = TokenContract.functions.balanceOf(owner).call()

                        # 残高がゼロではない場合、詳細情報を取得する
                        if balance == 0:
                            continue
                        else:
                            owner_address = TokenContract.functions.owner().call()
                            company_name, rsa_publickey = \
                                CouponMyTokens.get_company_name(company_list, owner_address)
                            name = TokenContract.functions.name().call()
                            symbol = TokenContract.functions.symbol().call()
                            total_supply = TokenContract.functions.totalSupply().call()
                            details = TokenContract.functions.details().call()
                            memo = TokenContract.functions.memo().call()
                            image_url_1 = TokenContract.functions.getImageURL(0).call()
                            image_url_2 = TokenContract.functions.getImageURL(1).call()
                            image_url_3 = TokenContract.functions.getImageURL(2).call()
                            status = TokenContract.functions.status().call()
                            contact_information = TokenContract.functions.contactInformation().call()
                            privacy_policy = TokenContract.functions.privacyPolicy().call()

                            jdr_token = JDRToken()
                            jdr_token.token_address = token_address
                            jdr_token.token_template = token_template
                            jdr_token.owner_address = owner_address
                            jdr_token.company_name = company_name
                            jdr_token.rsa_publickey = rsa_publickey
                            jdr_token.name = name
                            jdr_token.symbol = symbol
                            jdr_token.total_supply = total_supply
                            jdr_token.details = details
                            jdr_token.memo = memo
                            jdr_token.image_url = [
                                {'id': 1, 'url': image_url_1},
                                {'id': 2, 'url': image_url_2},
                                {'id': 3, 'url': image_url_3}
                            ]
                            jdr_token.status = status
                            jdr_token.payment_method_credit_card = token.payment_method_credit_card
                            jdr_token.payment_method_bank = token.payment_method_bank
                            jdr_token.contact_information = contact_information
                            jdr_token.privacy_policy = privacy_policy

                            position_list.append({
                                'token': jdr_token.__dict__,
                                'balance': balance
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
