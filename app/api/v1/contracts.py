# -*- coding: utf-8 -*-
import os
import json
import requests

from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Listing, BondToken, MembershipToken, CouponToken

LOG = log.get_logger()

# ------------------------------
# [普通社債]公開中トークン一覧
# ------------------------------
class Contracts(BaseResource):
    def __init__(self):
        super().__init__()
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    '''
    Handle for endpoint: /v1/StraightBond/Contracts
    '''
    def on_get(self, req, res):
        LOG.info('v1.contracts.Contracts')

        session = req.context["session"]

        # Validation
        request_json = Contracts.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).all()
        list_length = len(available_tokens)

        if request_json['cursor'] != None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        # 企業リストの情報を取得する
        company_list = []
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except:
            pass

        token_list = []
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if len(token_list) >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = ListContract.functions.\
                getTokenByAddress(token_address).call()

            token_detail = self.get_token_detail(token_id = i,
                                                 company_list = company_list,
                                                 token_address = token[0],
                                                 token_template = token[1],
                                                 owner_address = token[2],
                                                 available_token = available_tokens[i]
                                                 )
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)


    def get_token_detail(self, token_id, token_address, token_template, owner_address, company_list, available_token):
        """
        トークン詳細を取得する。
        取得に失敗した場合はNoneを返す。
        """

        if token_template == 'IbetStraightBond':
            try:
                # Token-Contractへの接続
                TokenContract = Contract.get_contract(
                    'IbetStraightBond',
                    to_checksum_address(token_address)
                )

                # 償還済みの銘柄はリストに返さない
                if TokenContract.functions.isRedeemed().call() == True:
                    return None

                # Token-Contractから情報を取得する
                name = TokenContract.functions.name().call()
                symbol = TokenContract.functions.symbol().call()
                total_supply = TokenContract.functions.totalSupply().call()
                face_value = TokenContract.functions.faceValue().call()
                interest_rate = TokenContract.functions.interestRate().call()

                interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()

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
                    interestPaymentDate = json.loads(
                        interestPaymentDate_string.replace("'", '"').\
                        replace('True', 'true').replace('False', 'false'))
                    if 'interestPaymentDate1' in interestPaymentDate:
                        interest_payment_date1 = interestPaymentDate['interestPaymentDate1']
                    if 'interestPaymentDate2' in interestPaymentDate:
                        interest_payment_date2 = interestPaymentDate['interestPaymentDate2']
                    if 'interestPaymentDate3' in interestPaymentDate:
                        interest_payment_date3 = interestPaymentDate['interestPaymentDate3']
                    if 'interestPaymentDate4' in interestPaymentDate:
                        interest_payment_date4 = interestPaymentDate['interestPaymentDate4']
                    if 'interestPaymentDate5' in interestPaymentDate:
                        interest_payment_date5 = interestPaymentDate['interestPaymentDate5']
                    if 'interestPaymentDate6' in interestPaymentDate:
                        interest_payment_date6 = interestPaymentDate['interestPaymentDate6']
                    if 'interestPaymentDate7' in interestPaymentDate:
                        interest_payment_date7 = interestPaymentDate['interestPaymentDate7']
                    if 'interestPaymentDate8' in interestPaymentDate:
                        interest_payment_date8 = interestPaymentDate['interestPaymentDate8']
                    if 'interestPaymentDate9' in interestPaymentDate:
                        interest_payment_date9 = interestPaymentDate['interestPaymentDate9']
                    if 'interestPaymentDate10' in interestPaymentDate:
                        interest_payment_date10 = interestPaymentDate['interestPaymentDate10']
                    if 'interestPaymentDate11' in interestPaymentDate:
                        interest_payment_date11 = interestPaymentDate['interestPaymentDate11']
                    if 'interestPaymentDate12' in interestPaymentDate:
                        interest_payment_date12 = interestPaymentDate['interestPaymentDate12']
                except:
                    pass

                redemption_date = TokenContract.functions.redemptionDate().call()
                redemption_amount = TokenContract.functions.redemptionAmount().call()
                return_date = TokenContract.functions.returnDate().call()
                return_amount = TokenContract.functions.returnAmount().call()
                purpose = TokenContract.functions.purpose().call()
                image_url_1 = TokenContract.functions.image_urls(0).call()
                image_url_2 = TokenContract.functions.image_urls(1).call()
                image_url_3 = TokenContract.functions.image_urls(2).call()
                contact_information = TokenContract.functions.contactInformation().call()
                privacy_policy = TokenContract.functions.privacyPolicy().call()

                # 企業リストから、企業名とRSA鍵を取得する
                company_name = ''
                rsa_publickey = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']
                        rsa_publickey = company['rsa_publickey']

                # 第三者認定（Sign）のイベント情報を検索する
                # NOTE:現状項目未使用であるため空のリストを返す
                certification = []

                bondtoken = BondToken()
                bondtoken.token_address = token_address
                bondtoken.token_template = token_template
                bondtoken.owner_address = owner_address
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
                        {'id':1, 'url':image_url_1},
                        {'id':2, 'url':image_url_2},
                        {'id':3, 'url':image_url_3},
                    ]
                bondtoken.certification = certification
                bondtoken.payment_method_credit_card = available_token.payment_method_credit_card
                bondtoken.payment_method_bank = available_token.payment_method_bank
                bondtoken.contact_information = contact_information
                bondtoken.privacy_policy = privacy_policy
                bondtoken = bondtoken.__dict__
                bondtoken['id'] = token_id

                return bondtoken
            except Exception as e:
                LOG.error(e)
                return None

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document

# ------------------------------
# [会員権]公開中トークン一覧
# ------------------------------
class MembershipContracts(BaseResource):
    def __init__(self):
        super().__init__()
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    '''
    Handle for endpoint: /v1/Membership/Contracts
    '''
    def on_get(self, req, res):
        LOG.info('v1.contracts.MembershipContracts')

        session = req.context["session"]

        # Validation
        request_json = MembershipContracts.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).all()
        list_length = len(available_tokens)

        if request_json['cursor'] != None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        # 企業リストの情報を取得する
        company_list = []
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except:
            pass

        token_list = []
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if len(token_list) >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = ListContract.functions.\
                getTokenByAddress(token_address).call()

            token_detail = self.get_token_detail(token_id = i,
                                                 company_list = company_list,
                                                 token_address = token[0],
                                                 token_template = token[1],
                                                 owner_address = token[2],
                                                 available_token = available_tokens[i])
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)


    def get_token_detail(self, token_id, token_address, token_template, owner_address, company_list, available_token):
        """
        トークン詳細を取得する。
        取得に失敗した場合はNoneを返す。
        """

        if token_template == 'IbetMembership':
            try:
                # Token-Contractへの接続
                TokenContract = Contract.get_contract(
                    'IbetMembership',
                    to_checksum_address(token_address)
                )

                # 取扱停止銘柄はリストに返さない
                if TokenContract.functions.status().call() == False:
                    return None

                # Token-Contractから情報を取得する
                name = TokenContract.functions.name().call()
                symbol = TokenContract.functions.symbol().call()
                total_supply = TokenContract.functions.totalSupply().call()
                details = TokenContract.functions.details().call()
                return_details = TokenContract.functions.returnDetails().call()
                expiration_date = TokenContract.functions.expirationDate().call()
                memo = TokenContract.functions.memo().call()
                transferable = TokenContract.functions.transferable().call()
                status = TokenContract.functions.status().call()
                image_url_1 = TokenContract.functions.image_urls(0).call()
                image_url_2 = TokenContract.functions.image_urls(1).call()
                image_url_3 = TokenContract.functions.image_urls(2).call()
                initial_offering_status = \
                    TokenContract.functions.initialOfferingStatus().call()
                contact_information = TokenContract.functions.contactInformation().call()
                privacy_policy = TokenContract.functions.privacyPolicy().call()

                # 企業リストから、企業名とRSA鍵を取得する
                company_name = ''
                rsa_publickey = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']
                        rsa_publickey = company['rsa_publickey']
                
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
                membershiptoken.initial_offering_status = initial_offering_status
                membershiptoken.image_url = [
                        {'id':1, 'url':image_url_1},
                        {'id':2, 'url':image_url_2},
                        {'id':3, 'url':image_url_3},
                    ]
                membershiptoken.payment_method_credit_card = available_token.payment_method_credit_card
                membershiptoken.payment_method_bank = available_token.payment_method_bank
                membershiptoken.contact_information = contact_information
                membershiptoken.privacy_policy = privacy_policy
                membershiptoken = membershiptoken.__dict__
                membershiptoken['id'] = token_id

                return membershiptoken
            except Exception as e:
                LOG.error(e)
                return None

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document

# ------------------------------
# [クーポン]公開中トークン一覧
# ------------------------------
class CouponContracts(BaseResource):
    def __init__(self):
        super().__init__()
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    '''
    Handle for endpoint: /v1/Coupon/Contracts
    '''
    def on_get(self, req, res):
        LOG.info('v1.contracts.CouponContracts')

        session = req.context["session"]

        # Validation
        request_json = CouponContracts.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).all()
        list_length = len(available_tokens)

        if request_json['cursor'] != None and request_json['cursor'] > list_length:
            raise InvalidParameterError(
                "cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        # 企業リストの情報を取得する
        company_list = []
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except:
            pass

        token_list = []
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if len(token_list) >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = ListContract.functions.\
                getTokenByAddress(token_address).call()

            token_detail = self.get_token_detail(
                token_id = i,
                company_list = company_list,
                token_address = token[0],
                token_template = token[1],
                owner_address = token[2],
                available_token = available_tokens[i]
            )
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)

    def get_token_detail(self, token_id, token_address, token_template,
        owner_address, company_list, available_token):
        """
        トークン詳細を取得する。
        取得に失敗した場合はNoneを返す。
        """
        
        if token_template == 'IbetCoupon':
            try:
                # Token-Contractへの接続
                TokenContract = Contract.get_contract(
                    'IbetCoupon',
                    to_checksum_address(token_address)
                )

                # 取扱停止銘柄はリストに返さない
                if TokenContract.functions.status().call() == False:
                    return None

                # Token-Contractから情報を取得する
                name = TokenContract.functions.name().call()
                symbol = TokenContract.functions.symbol().call()
                total_supply = TokenContract.functions.totalSupply().call()
                details = TokenContract.functions.details().call()
                return_details = TokenContract.functions.returnDetails().call()
                expiration_date = TokenContract.functions.expirationDate().call()
                memo = TokenContract.functions.memo().call()
                transferable = TokenContract.functions.transferable().call()
                status = TokenContract.functions.status().call()
                image_url_1 = TokenContract.functions.image_urls(0).call()
                image_url_2 = TokenContract.functions.image_urls(1).call()
                image_url_3 = TokenContract.functions.image_urls(2).call()
                initial_offering_status = \
                    TokenContract.functions.initialOfferingStatus().call()
                contact_information = TokenContract.functions.contactInformation().call()
                privacy_policy = TokenContract.functions.privacyPolicy().call()

                # 企業リストから、企業名とRSA鍵を取得する
                company_name = ''
                rsa_publickey = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']
                        rsa_publickey = company['rsa_publickey']
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
                coupontoken.expiration_date = expiration_date
                coupontoken.memo = memo
                coupontoken.transferable = transferable
                coupontoken.status = status
                coupontoken.initial_offering_status = initial_offering_status
                coupontoken.image_url = [
                        {'id':1, 'url':image_url_1},
                        {'id':2, 'url':image_url_2},
                        {'id':3, 'url':image_url_3},
                    ]
                coupontoken.payment_method_credit_card = available_token.payment_method_credit_card
                coupontoken.payment_method_bank = available_token.payment_method_bank
                coupontoken.contact_information = contact_information
                coupontoken.privacy_policy = privacy_policy
                coupontoken = coupontoken.__dict__
                coupontoken['id'] = token_id

                return coupontoken
            except Exception as e:
                LOG.error(e)
                return None

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min':0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document
