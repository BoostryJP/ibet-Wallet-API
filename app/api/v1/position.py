# -*- coding: utf-8 -*-
import json
import requests
import os

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

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        position_list = []
        for buy_address in request_json['account_address_list']:
            portfolio_list = []
            # 約定イベントから買い注文アドレスが一致するイベントを抽出する
            try:
                event_filter = ExchangeContract.events.Agree.createFilter(
                    fromBlock='earliest',
                    argument_filters={'buyAddress': to_checksum_address(buy_address)}
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

            # トークン送信イベントから送信先アドレスが一致するイベントを抽出する
            try:
                event_filter = ExchangeContract.events.Transfer.createFilter(
                    fromBlock='earliest',
                    argument_filters={'to': to_checksum_address(buy_address)}
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

            # リストをユニークにする
            portfolio_list_uniq = []
            for portfolio in portfolio_list:
                if portfolio not in portfolio_list_uniq:
                    portfolio_list_uniq.append(portfolio)

            # 残高（balance）、残注文（commitment）を取得する
            #token_template = None
            for mytoken in portfolio_list_uniq:
                token_address = to_checksum_address(mytoken['token_address'])
                #token_template = ListContract.functions.getTokenByAddress(token_address).call()
                #if token_template[0] == '0x0000000000000000000000000000000000000000':
                #    continue
                TokenContract = Contract.get_contract(
                    'IbetStraightBond', token_address)

                owner = to_checksum_address(mytoken['account'])
                balance = TokenContract.functions.balanceOf(owner).call()
                commitment = ExchangeContract.functions.\
                    commitments(owner, token_address).call()

                # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                if balance == 0 and commitment == 0:
                    continue
                else:
                    name = TokenContract.functions.name().call()
                    symbol = TokenContract.functions.symbol().call()
                    totalSupply = TokenContract.functions.totalSupply().call()
                    faceValue = TokenContract.functions.faceValue().call()
                    interestRate = TokenContract.functions.interestRate().call()

                    interestPaymentDate_string = TokenContract.functions.\
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

                    redemptionDate = TokenContract.functions.redemptionDate().call()
                    redemptionAmount = TokenContract.functions.redemptionAmount().call()
                    returnDate = TokenContract.functions.returnDate().call()
                    returnAmount = TokenContract.functions.returnAmount().call()
                    purpose = TokenContract.functions.purpose().call()
                    image_url_small = TokenContract.functions.getImageURL(0).call()
                    image_url_medium = TokenContract.functions.getImageURL(1).call()
                    image_url_large = TokenContract.functions.getImageURL(2).call()
                    owner_address = TokenContract.functions.owner().call()

                    # 企業リストから、企業名を取得する
                    company_name = ''
                    for company in company_list:
                        if to_checksum_address(company['address']) == owner_address:
                            company_name = company['corporate_name']

                    # 第三者認定（Sign）のイベント情報を検索する
                    event_filter = TokenContract.events.Sign.createFilter(fromBlock='earliest')
                    try:
                        entries = event_filter.get_all_entries()
                    except:
                        entries = []
                    web3.eth.uninstallFilter(event_filter.filter_id)

                    certification = []
                    for entry in entries:
                        isSigned = False
                        if TokenContract.functions.\
                            signatures(to_checksum_address(entry['args']['signer'])).call() == 2:
                            isSigned = True

                        certification.append({
                            'signer':entry['args']['signer'],
                            'is_signed':isSigned
                        })

                    position_list.append({
                        'token': {
                            'token_address': mytoken['token_address'],
                            #'token_template': token_template[1],
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
