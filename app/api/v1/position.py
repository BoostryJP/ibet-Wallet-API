# -*- coding: utf-8 -*-
import json
import requests
import os
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), 'JST')

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Listing

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

# ------------------------------
# [普通社債]保有トークン一覧
# ------------------------------
class MyTokens(BaseResource):

    '''
    Handle for endpoint: /v1/MyTokens/
    '''
    def on_post(self, req, res):
        LOG.info('v1.Position.MyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = MyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # Company List：発行体企業リスト
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except:
            company_list = []

        # Bond Exchange Contract
        BondExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        position_list = []
        for _account_address in request_json['account_address_list']:
            available_tokens = session.query(Listing).all()

            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in available_tokens:
                token_info = ListContract.functions.\
                    getTokenByAddress(token.token_address).call()

                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetStraightBond':
                    BondTokenContract = Contract.\
                        get_contract('IbetStraightBond', token_address)
                    try:
                        balance = BondTokenContract.functions.balanceOf(owner).call()
                        commitment = BondExchangeContract.functions.\
                            commitments(owner, token_address).call()

                        # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                        # Note: 現状は、債券トークンの場合、残高・残注文ゼロの場合は詳細情報を
                        #       返さない仕様としている。
                        if balance == 0 and commitment == 0:
                            continue
                        else:
                            name = BondTokenContract.functions.name().call()
                            symbol = BondTokenContract.functions.symbol().call()
                            totalSupply = BondTokenContract.functions.totalSupply().call()
                            faceValue = BondTokenContract.functions.faceValue().call()
                            interestRate = BondTokenContract.functions.interestRate().call()

                            interestPaymentDate_string = \
                                BondTokenContract.functions.interestPaymentDate().call()
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

                            redemptionDate = BondTokenContract.functions.redemptionDate().call()
                            redemptionAmount = BondTokenContract.functions.redemptionAmount().call()
                            returnDate = BondTokenContract.functions.returnDate().call()
                            returnAmount = BondTokenContract.functions.returnAmount().call()
                            purpose = BondTokenContract.functions.purpose().call()
                            image_url_1 = BondTokenContract.functions.getImageURL(0).call()
                            image_url_2 = BondTokenContract.functions.getImageURL(1).call()
                            image_url_3 = BondTokenContract.functions.getImageURL(2).call()
                            owner_address = BondTokenContract.functions.owner().call()
                            company_name, rsa_publickey = \
                                MyTokens.get_company_name(company_list, owner_address)

                            # 第三者認定（Sign）のイベント情報を検索する
                            # NOTE:現状項目未使用であるため空のリストを返す
                            certification = []

                            position_list.append({
                                'token': {
                                    'token_address': token_address,
                                    'token_template': token_template,
                                    'company_name': company_name,
                                    'rsa_publickey': rsa_publickey,
                                    'name': name,
                                    'symbol': symbol,
                                    'totalSupply': totalSupply,
                                    'faceValue': faceValue,
                                    'interestRate': interestRate,
                                    'interestPaymentDate1':interestPaymentDate1,
                                    'interestPaymentDate2':interestPaymentDate2,
                                    'interestPaymentDate3':interestPaymentDate3,
                                    'interestPaymentDate4':interestPaymentDate4,
                                    'interestPaymentDate5':interestPaymentDate5,
                                    'interestPaymentDate6':interestPaymentDate6,
                                    'interestPaymentDate7':interestPaymentDate7,
                                    'interestPaymentDate8':interestPaymentDate8,
                                    'interestPaymentDate9':interestPaymentDate9,
                                    'interestPaymentDate10':interestPaymentDate10,
                                    'interestPaymentDate11':interestPaymentDate11,
                                    'interestPaymentDate12':interestPaymentDate12,
                                    'redemptionDate': redemptionDate,
                                    'redemptionAmount': redemptionAmount,
                                    'returnDate': returnDate,
                                    'returnAmount': returnAmount,
                                    'purpose': purpose,
                                    'image_url': [
                                        {'id': 1, 'url': image_url_1},
                                        {'id': 2, 'url': image_url_2},
                                        {'id': 3, 'url': image_url_3}
                                    ],
                                    'certification': certification
                                },
                                'balance': balance,
                                'commitment': commitment
                            })
                    except:
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

    '''
    Handle for endpoint: /v1/Membership/MyTokens/
    '''
    def on_post(self, req, res):
        LOG.info('v1.Position.MembershipMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = MembershipMyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # Company List：発行体企業リスト
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except:
            company_list = []

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange',
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS')
        )

        position_list = []
        for _account_address in request_json['account_address_list']:
            available_tokens = session.query(Listing).all()

            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in available_tokens:
                token_info = ListContract.functions.\
                    getTokenByAddress(token.token_address).call()

                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetMembership':
                    TokenContract = Contract.\
                        get_contract('IbetMembership', token_address)
                    try:
                        balance = TokenContract.functions.balanceOf(owner).call()
                        commitment = ExchangeContract.functions.\
                            commitments(owner, token_address).call()

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
                            company_name, rsa_publickey = MembershipMyTokens.\
                                get_company_name(company_list, owner_address)

                            position_list.append({
                                'token': {
                                    'token_address': token_address,
                                    'token_template': token_template,
                                    'company_name': company_name,
                                    'rsa_publickey': rsa_publickey,
                                    'name': name,
                                    'symbol': symbol,
                                    'total_supply': total_supply,
                                    'details': details,
                                    'return_details': return_details,
                                    'expiration_date': expiration_date,
                                    'memo': memo,
                                    'transferable': transferable,
                                    'status': status,
                                    'image_url': [
                                        {'id': 1, 'url': image_url_1},
                                        {'id': 2, 'url': image_url_2},
                                        {'id': 3, 'url': image_url_3}
                                    ],
                                },
                                'balance': balance,
                                'commitment': commitment
                            })
                    except:
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

    '''
    Handle for endpoint: /v1/Coupon/MyTokens/
    '''
    def on_post(self, req, res):
        LOG.info('v1.Position.CouponMyTokens')

        session = req.context["session"]

        # 入力値チェック
        request_json = CouponMyTokens.validate(req)

        # Company List：発行体企業リスト
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except:
            company_list = []

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # Coupon Exchange Contract
        CouponExchangeContract = Contract.get_contract(
            'IbetCouponExchange', os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        position_list = []
        for _account_address in request_json['account_address_list']:
            available_tokens = session.query(Listing).all()

            # 取扱トークンリスト1件ずつトークンの詳細情報を取得していく
            for token in available_tokens:
                token_info = ListContract.functions.\
                    getTokenByAddress(token.token_address).call()

                token_address = token_info[0]
                token_template = token_info[1]
                owner = to_checksum_address(_account_address)

                if token_template == 'IbetCoupon':
                    CouponTokenContract = \
                        Contract.get_contract('IbetCoupon', token_address)
                    try:
                        balance = CouponTokenContract.functions.balanceOf(owner).call()
                        commitment = CouponExchangeContract.functions.\
                            commitments(owner, token_address).call()
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
                            totalSupply = CouponTokenContract.functions.totalSupply().call()
                            details = CouponTokenContract.functions.details().call()
                            memo = CouponTokenContract.functions.memo().call()
                            expirationDate = CouponTokenContract.functions.expirationDate().call()
                            transferable = CouponTokenContract.functions.transferable().call()
                            image_url_1 = CouponTokenContract.functions.getImageURL(0).call()
                            image_url_2 = CouponTokenContract.functions.getImageURL(1).call()
                            image_url_3 = CouponTokenContract.functions.getImageURL(2).call()
                            status = CouponTokenContract.functions.status().call()

                            position_list.append({
                                'token': {
                                    'token_address': token_address,
                                    'token_template': token_template,
                                    'owner_address': owner_address,
                                    'company_name': company_name,
                                    'rsa_publickey': rsa_publickey,
                                    'name': name,
                                    'symbol': symbol,
                                    'totalSupply': totalSupply,
                                    'details': details,
                                    'memo': memo,
                                    'expirationDate': expirationDate,
                                    'transferable': transferable,
                                    'image_url': [
                                        {'id': 1, 'url': image_url_1},
                                        {'id': 2, 'url': image_url_2},
                                        {'id': 3, 'url': image_url_3}
                                    ],
                                    'status': status,
                                },
                                'balance': balance,
                                'commitment': commitment,
                                'used': used
                            })

                    except:
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
# クーポン消費履歴
# ------------------------------
class CouponConsumptions(BaseResource):

    '''
    Handle for endpoint: /v1/CouponConsumptions/
    '''
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
                            web3.eth.getBlock(entry['blockNumber'])['timestamp'],JST).\
                            strftime("%Y/%m/%d %H:%M:%S"),
                        'value': entry['args']['value']
                    })
            except:
                pass

        # block_timestampの昇順にソートする
        # Note: もともとのリストはaccountのリストでループして作成したリストなので、古い順になっていないため
        coupon_consumptions = sorted(
            coupon_consumptions,
            key=lambda x:x['block_timestamp']
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
