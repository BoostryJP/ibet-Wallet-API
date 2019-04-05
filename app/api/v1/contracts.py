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
    Handle for endpoint: /v1/Contracts
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
                                                 available_tokens = available_tokens[i]
                                                 )
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)


    def get_token_detail(self, token_id, token_address, token_template, owner_address, company_list, available_tokens):
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
                totalSupply = TokenContract.functions.totalSupply().call()
                faceValue = TokenContract.functions.faceValue().call()
                interestRate = TokenContract.functions.interestRate().call()

                interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()

                interestPaymentDate1 = ''
                interestPaymentDate2 = ''
                interestPaymentDate3 = ''
                interestPaymentDate4 = ''
                interestPaymentDate5 = ''
                interestPaymentDate6 = ''
                interestPaymentDate7 = ''
                interestPaymentDate8 = ''
                interestPaymentDate9 = ''
                interestPaymentDate10 = ''
                interestPaymentDate11 = ''
                interestPaymentDate12 = ''

                try:
                    interestPaymentDate = json.loads(
                        interestPaymentDate_string.replace("'", '"').\
                        replace('True', 'true').replace('False', 'false'))
                    if 'interestPaymentDate1' in interestPaymentDate:
                        interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                    if 'interestPaymentDate2' in interestPaymentDate:
                        interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']
                    if 'interestPaymentDate3' in interestPaymentDate:
                        interestPaymentDate3 = interestPaymentDate['interestPaymentDate3']
                    if 'interestPaymentDate4' in interestPaymentDate:
                        interestPaymentDate4 = interestPaymentDate['interestPaymentDate4']
                    if 'interestPaymentDate5' in interestPaymentDate:
                        interestPaymentDate5 = interestPaymentDate['interestPaymentDate5']
                    if 'interestPaymentDate6' in interestPaymentDate:
                        interestPaymentDate6 = interestPaymentDate['interestPaymentDate6']
                    if 'interestPaymentDate7' in interestPaymentDate:
                        interestPaymentDate7 = interestPaymentDate['interestPaymentDate7']
                    if 'interestPaymentDate8' in interestPaymentDate:
                        interestPaymentDate8 = interestPaymentDate['interestPaymentDate8']
                    if 'interestPaymentDate9' in interestPaymentDate:
                        interestPaymentDate9 = interestPaymentDate['interestPaymentDate9']
                    if 'interestPaymentDate10' in interestPaymentDate:
                        interestPaymentDate10 = interestPaymentDate['interestPaymentDate10']
                    if 'interestPaymentDate11' in interestPaymentDate:
                        interestPaymentDate11 = interestPaymentDate['interestPaymentDate11']
                    if 'interestPaymentDate12' in interestPaymentDate:
                        interestPaymentDate12 = interestPaymentDate['interestPaymentDate12']
                except:
                    pass

                redemptionDate = TokenContract.functions.redemptionDate().call()
                redemptionAmount = TokenContract.functions.redemptionAmount().call()
                returnDate = TokenContract.functions.returnDate().call()
                returnAmount = TokenContract.functions.returnAmount().call()
                purpose = TokenContract.functions.purpose().call()
                image_url_1 = TokenContract.functions.image_urls(0).call()
                image_url_2 = TokenContract.functions.image_urls(1).call()
                image_url_3 = TokenContract.functions.image_urls(2).call()

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
                bondtoken['id'] = token_id
                bondtoken.tokenAddress = token_address
                bondtoken.tokenTemplate = token_template
                bondtoken.ownerAddress = owner_address
                bondtoken.companyName = company_name
                bondtoken.rsaPublickey = rsa_publickey
                bondtoken.name = name
                bondtoken.symbol = symbol
                bondtoken.totalSupply = totalSupply
                bondtoken.faceValue = faceValue
                bondtoken.interestRate = interestRate
                bondtoken.interestPaymentDate1 = interestPaymentDate1
                bondtoken.interestPaymentDate2 = interestPaymentDate2
                bondtoken.interestPaymentDate3 = interestPaymentDate3
                bondtoken.interestPaymentDate4 = interestPaymentDate4
                bondtoken.interestPaymentDate5 = interestPaymentDate5
                bondtoken.interestPaymentDate6 = interestPaymentDate6
                bondtoken.interestPaymentDate7 = interestPaymentDate7
                bondtoken.interestPaymentDate8 = interestPaymentDate8
                bondtoken.interestPaymentDate9 = interestPaymentDate9
                bondtoken.interestPaymentDate10 = interestPaymentDate10
                bondtoken.interestPaymentDate11 = interestPaymentDate11
                bondtoken.interestPaymentDate12 = interestPaymentDate12
                bondtoken.redemptionDate = redemptionDate
                bondtoken.redemptionAmount = redemptionAmount
                bondtoken.returnDate = returnDate
                bondtoken.returnAmount = returnAmount
                bondtoken.purpose = purpose
                bondtoken.imageUrl = [
                        {'id':1, 'url':image_url_1},
                        {'id':2, 'url':image_url_2},
                        {'id':3, 'url':image_url_3},
                    ]
                bondtoken.certification = certification
                bondtoken.creditCardAvailability = available_tokens.credit_card_availability
                bondtoken.bankPaymentAvailability = available_tokens.bank_payment_availability

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
                                                 available_tokens = available_tokens[i])
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)


    def get_token_detail(self, token_id, token_address, token_template, owner_address, company_list, available_tokens):
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
                totalSupply = TokenContract.functions.totalSupply().call()
                details = TokenContract.functions.details().call()
                returnDetails = TokenContract.functions.returnDetails().call()
                expirationDate = TokenContract.functions.expirationDate().call()
                memo = TokenContract.functions.memo().call()
                transferable = TokenContract.functions.transferable().call()
                status = TokenContract.functions.status().call()

                image_url_1 = TokenContract.functions.image_urls(0).call()
                image_url_2 = TokenContract.functions.image_urls(1).call()
                image_url_3 = TokenContract.functions.image_urls(2).call()

                initial_offering_status = \
                    TokenContract.functions.initialOfferingStatus().call()

                # 企業リストから、企業名とRSA鍵を取得する
                company_name = ''
                rsa_publickey = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']
                        rsa_publickey = company['rsa_publickey']
                
                membershiptoken = MembershipToken()
                membershiptoken['id'] = token_id
                membershiptoken.tokenAddress = token_address
                membershiptoken.tokenTemplate = token_template
                membershiptoken.ownerAddress = owner_address
                membershiptoken.companyName = company_name
                membershiptoken.rsaPublickey = rsa_publickey
                membershiptoken.name = name
                membershiptoken.symbol = symbol
                membershiptoken.totalSupply = totalSupply
                membershiptoken.details = details
                membershiptoken.returnDetails = returnDetails
                membershiptoken.expirationDate = expirationDate
                membershiptoken.memo = memo
                membershiptoken.transferable = transferable
                membershiptoken.status = status
                membershiptoken.initialOfferingStatus = initialOfferingStatus
                membershiptoken.imageUrl = [
                        {'id':1, 'url':image_url_1},
                        {'id':2, 'url':image_url_2},
                        {'id':3, 'url':image_url_3},
                    ]
                membershiptoken.creditCardAvailability = available_tokens.credit_card_availability
                membershiptoken.bankPaymentAvailability = available_tokens.bank_payment_availability

                return membershiptoken
            except Exception as e:
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
                owner_address = token[2]
            )
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)

    def get_token_detail(self, token_id, token_address, token_template,
        owner_address, company_list):
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
                totalSupply = TokenContract.functions.totalSupply().call()
                details = TokenContract.functions.details().call()
                return_details = TokenContract.functions.returnDetails().call()
                expirationDate = TokenContract.functions.expirationDate().call()
                memo = TokenContract.functions.memo().call()
                transferable = TokenContract.functions.transferable().call()
                status = TokenContract.functions.status().call()

                image_url_1 = TokenContract.functions.image_urls(0).call()
                image_url_2 = TokenContract.functions.image_urls(1).call()
                image_url_3 = TokenContract.functions.image_urls(2).call()

                initial_offering_status = \
                    TokenContract.functions.initialOfferingStatus().call()

                # 企業リストから、企業名とRSA鍵を取得する
                company_name = ''
                rsa_publickey = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']
                        rsa_publickey = company['rsa_publickey']
                coupontoken = CouponToken()
                coupontoken['id'] = token_id
                coupontoken.tokenAddress = token_address
                coupontoken.tokenTemplate = token_template
                coupontoken.ownerAddress = owner_address
                coupontoken.companyName = company_name
                coupontoken.rsaPublickey = rsa_publickey
                coupontoken.name = name
                coupontoken.symbol = symbol
                coupontoken.totalSupply = totalSupply
                coupontoken.details = details
                coupontoken.returnDetails = returnDetails
                coupontoken.expirationDate = expirationDate
                coupontoken.memo = memo
                coupontoken.transferable = transferable
                coupontoken.status = status
                coupontoken.initialOfferingStatus = initialOfferingStatus
                coupontoken.imageUrl = [
                        {'id':1, 'url':image_url_1},
                        {'id':2, 'url':image_url_2},
                        {'id':3, 'url':image_url_3},
                    ]
                coupontoken.creditCardAvailability = available_tokens.credit_card_availability
                coupontoken.bankPaymentAvailability = available_tokens.bank_payment_availability

                return coupontoken
            except Exception as e:
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
