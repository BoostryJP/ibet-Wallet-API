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
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config
from app.contracts import Contract

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

# ------------------------------
# 保有トークン一覧
# ------------------------------
class MyTokens(BaseResource):

    '''
    Handle for endpoint: /v1/MyTokens/
    '''
    def on_post(self, req, res):
        LOG.info('v1.Position.MyTokens')

        request_json = MyTokens.validate(req)

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            company_list = []

        # Bond Exchange Contract
        BondExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        # Coupon Exchange Contract
        CouponExchangeContract = Contract.get_contract(
            'IbetCouponExchange', os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        position_list = []
        for _account_address in request_json['account_address_list']:
            portfolio_list = []

            # イベント抽出
            #  IbetStraightBond（約定イベント）
            #  _account_addressと『買注文アドレス』が一致するイベントを抽出する。
            try:
                event_filter = BondExchangeContract.events.Agree.createFilter(
                    fromBlock='earliest',
                    argument_filters={'buyAddress': to_checksum_address(_account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    portfolio_list.append({
                        'account': entry['args']['buyAddress'],
                        'token_address': entry['args']['tokenAddress'],
                    })
            except:
                pass

            # イベント抽出
            #  IbetStraightBond（トークン送信イベント）
            #  _account_addressと『送信先アドレス』が一致するイベントを抽出する。
            try:
                event_filter = BondExchangeContract.events.Transfer.createFilter(
                    fromBlock='earliest',
                    argument_filters={'to': to_checksum_address(_account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    portfolio_list.append({
                        'account': entry['args']['to'],
                        'token_address': entry['args']['tokenAddress'],
                    })
            except:
                pass

            # イベント抽出
            #  IbetCoupon（トークン送信イベント）
            #  _account_addressと『送信先アドレス』が一致するイベントを抽出する。
            try:
                event_filter = CouponExchangeContract.events.Transfer.createFilter(
                    fromBlock='earliest',
                    argument_filters={'to': to_checksum_address(_account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    portfolio_list.append({
                        'account': entry['args']['to'],
                        'token_address': entry['args']['tokenAddress'],
                    })
            except:
                pass

            # リストをユニークにして、保有候補リストを取得する
            # Note: ここで取得されたリストのトークンを全て保有しているとは限らない。
            #       例えば、既に売却済みのトークンも保有候補リストには含まれている。
            portfolio_list_uniq = []
            for portfolio in portfolio_list:
                if portfolio not in portfolio_list_uniq:
                    portfolio_list_uniq.append(portfolio)

            # token_addressの昇順にソートする
            portfolio_list_uniq = sorted(
                portfolio_list_uniq,
                key=lambda x:x['token_address']
            )

            # 保有候補リストに対して1件ずつトークンの詳細情報を取得していく
            for item in portfolio_list_uniq:
                owner = to_checksum_address(item['account'])
                token_address = to_checksum_address(item['token_address'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()

                # 1) TokenListに未登録の場合
                #    → クーポントークンの詳細情報を取得する
                # 2) TokenListに登録済の場合
                #    → 債券トークンの詳細情報を取得する
                if token_template[0] == '0x0000000000000000000000000000000000000000': # 未登録の場合
                    CouponTokenContract = Contract.get_contract('IbetCoupon', token_address)
                    try:
                        isValid = CouponTokenContract.functions.isValid().call()
                        if isValid == False:
                            continue
                        else:
                            owner_address = CouponTokenContract.functions.owner().call()
                            company_name = MyTokens.get_company_name(company_list, owner_address)
                            name = CouponTokenContract.functions.name().call()
                            symbol = CouponTokenContract.functions.symbol().call()
                            totalSupply = CouponTokenContract.functions.totalSupply().call()
                            details = CouponTokenContract.functions.details().call()
                            memo = CouponTokenContract.functions.memo().call()
                            expirationDate = CouponTokenContract.functions.expirationDate().call()
                            transferable = CouponTokenContract.functions.transferable().call()
                            image_url_small = CouponTokenContract.functions.getImageURL(0).call()
                            image_url_medium = CouponTokenContract.functions.getImageURL(1).call()
                            image_url_large = CouponTokenContract.functions.getImageURL(2).call()
                            balance = CouponTokenContract.functions.balanceOf(owner).call()
                            used = CouponTokenContract.functions.usedOf(owner).call()
                            position_list.append({
                                'token': {
                                    'token_address': token_address,
                                    'token_template': 'IbetCoupon',
                                    'owner_address': owner_address,
                                    'company_name': company_name,
                                    'name': name,
                                    'symbol': symbol,
                                    'totalSupply': totalSupply,
                                    'details': details,
                                    'memo': memo,
                                    'expirationDate': expirationDate,
                                    'transferable': transferable,
                                    'image_url': [
                                        {'type': 'small', 'url': image_url_small},
                                        {'type': 'medium', 'url': image_url_medium},
                                        {'type': "large", 'url': image_url_large}
                                    ],
                                },
                                'balance': balance,
                                'used': used
                            })
                    except:
                        continue
                else: # 登録済みの場合
                    if token_template[1] == 'IbetStraightBond':
                        BondTokenContract = Contract.\
                            get_contract('IbetStraightBond', token_address)
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

                            interestPaymentDate_string = BondTokenContract.functions.\
                                interestPaymentDate().call()
                            interestPaymentDate1 = ''
                            interestPaymentDate2 = ''
                            interestPaymentDate3 = ''
                            interestPaymentDate4 = ''
                            interestPaymentDate5 = ''
                            interestPaymentDate6 = ''
                            interestPaymentDate7 = ''
                            interestPaymentDate7 = ''
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
                            image_url_small = BondTokenContract.functions.getImageURL(0).call()
                            image_url_medium = BondTokenContract.functions.getImageURL(1).call()
                            image_url_large = BondTokenContract.functions.getImageURL(2).call()
                            owner_address = BondTokenContract.functions.owner().call()
                            company_name = MyTokens.get_company_name(company_list, owner_address)

                            # 第三者認定（Sign）のイベント情報を検索する
                            event_filter = BondTokenContract.events.Sign.createFilter(fromBlock='earliest')
                            try:
                                entries = event_filter.get_all_entries()
                            except:
                                entries = []
                            web3.eth.uninstallFilter(event_filter.filter_id)

                            certification = []
                            for entry in entries:
                                isSigned = False
                                if BondTokenContract.functions.\
                                    signatures(to_checksum_address(entry['args']['signer'])).call() == 2:
                                    isSigned = True

                                certification.append({
                                    'signer':entry['args']['signer'],
                                    'is_signed':isSigned
                                })

                            position_list.append({
                                'token': {
                                    'token_address': token_address,
                                    'token_template': token_template[1],
                                    'company_name': company_name,
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
                                        {'type': 'small', 'url': image_url_small},
                                        {'type': 'medium', 'url': image_url_medium},
                                        {'type': "large", 'url': image_url_large}
                                    ],
                                    'certification': certification
                                },
                                'balance': balance,
                                'commitment': commitment
                            })

        self.on_success(res, position_list)

    @staticmethod
    def get_company_name(company_list, owner_address):
        company_name = ''
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
        return company_name

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
