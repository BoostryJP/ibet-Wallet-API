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
# 注文一覧・約定一覧
# ------------------------------
class OrderList(BaseResource):
    '''
    Handle for endpoint: /v1/OrderList/
    '''
    def on_post(self, req, res):
        LOG.info('v1.OrderList.OrderList')

        request_json = OrderList.validate(req)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange',
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        )

        # TokenList Contract
        ListContract = Contract.get_contract(
            'TokenList', os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS'))

        # 企業リストの情報を取得する
        company_list = []
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            pass

        # 1) 注文一覧
        order_list = []
        for account_address in request_json['account_address_list']:
            try:
                # 指定したアカウントアドレスから発生している注文イベントを抽出する
                event_filter = ExchangeContract.events.NewOrder.createFilter(
                    fromBlock='earliest',
                    argument_filters={'accountAddress': to_checksum_address(account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    order_id = entry['args']['orderId']
                    orderBook = ExchangeContract.functions.orderBook(order_id).call()
                    # 残注文ゼロの場合は以下の処理をSKIP
                    if orderBook[2] != 0:
                        token_address = to_checksum_address(orderBook[1])
                        token_template = ListContract.functions.getTokenByAddress(token_address).call()
                        if token_template[0] == '0x0000000000000000000000000000000000000000':
                            continue

                        # Token-Contractへの接続
                        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

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

                        order_list.append({
                            'token':{
                                'token_address': token_address,
                                'token_template': token_template[1],
                                'company_name': company_name,
                                'name':name,
                                'symbol':symbol,
                                'totalSupply':totalSupply,
                                'faceValue':faceValue,
                                'interestRate':interestRate,
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
                                'redemptionDate':redemptionDate,
                                'redemptionAmount':redemptionAmount,
                                'returnDate':returnDate,
                                'returnAmount':returnAmount,
                                'purpose':purpose,
                                'image_url': [
                                    {'type': 'small', 'url': image_url_small},
                                    {'type': 'medium', 'url': image_url_medium},
                                    {'type': "large", 'url': image_url_large}
                                ],
                                'certification':certification
                            },
                            'order':{
                                'order_id':order_id,
                                'amount':orderBook[2],
                                'price':orderBook[3],
                                'isBuy':orderBook[4],
                                'canceled':orderBook[6]
                            }
                        })

            except:
                continue

        # 2) 決済中一覧
        settlement_list = []
        for account_address in request_json['account_address_list']:
            try:
                # 指定したアカウントアドレスから発生している約定イベント（買）を抽出する
                event_filter = ExchangeContract.events.Agree.createFilter(
                    fromBlock='earliest',
                    argument_filters={'buyAddress': to_checksum_address(account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    order_id = entry['args']['orderId']
                    agreement_id = entry['args']['agreementId']
                    agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
                    # 未決済状態のもののみ以降の処理を実施
                    if agreement[4] == False:
                        token_address = to_checksum_address(entry['args']['tokenAddress'])
                        token_template = ListContract.functions.getTokenByAddress(token_address).call()
                        if token_template[0] == '0x0000000000000000000000000000000000000000':
                            continue

                        # Token-Contractへの接続
                        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

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

                        settlement_list.append({
                            'token':{
                                'token_address': token_address,
                                'token_template': token_template[1],
                                'company_name': company_name,
                                'name':name,
                                'symbol':symbol,
                                'totalSupply':totalSupply,
                                'faceValue':faceValue,
                                'interestRate':interestRate,
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
                                'redemptionDate':redemptionDate,
                                'redemptionAmount':redemptionAmount,
                                'returnDate':returnDate,
                                'returnAmount':returnAmount,
                                'purpose':purpose,
                                'image_url': [
                                    {'type': 'small', 'url': image_url_small},
                                    {'type': 'medium', 'url': image_url_medium},
                                    {'type': "large", 'url': image_url_large}
                                ],
                                'certification':certification
                            },
                            'agreement':{
                                'order_id':order_id,
                                'agreementId':agreement_id,
                                'amount':agreement[1],
                                'price':agreement[2],
                                'isBuy':True,
                                'canceled':agreement[3]
                            }
                        })

                # 指定したアカウントアドレスから発生している約定イベント（売）を抽出する
                event_filter = ExchangeContract.events.Agree.createFilter(
                    fromBlock='earliest',
                    argument_filters={'sellAddress': to_checksum_address(account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    order_id = entry['args']['orderId']
                    agreement_id = entry['args']['agreementId']
                    agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
                    # 未決済状態のもののみ以降の処理を実施
                    if agreement[4] == False:
                        token_address = to_checksum_address(entry['args']['tokenAddress'])
                        token_template = ListContract.functions.getTokenByAddress(token_address).call()
                        if token_template[0] == '0x0000000000000000000000000000000000000000':
                            continue

                        # Token-Contractへの接続
                        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

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

                        settlement_list.append({
                            'token':{
                                'token_address': token_address,
                                'token_template': token_template[1],
                                'company_name': company_name,
                                'name':name,
                                'symbol':symbol,
                                'totalSupply':totalSupply,
                                'faceValue':faceValue,
                                'interestRate':interestRate,
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
                                'redemptionDate':redemptionDate,
                                'redemptionAmount':redemptionAmount,
                                'returnDate':returnDate,
                                'returnAmount':returnAmount,
                                'purpose':purpose,
                                'image_url': [
                                    {'type': 'small', 'url': image_url_small},
                                    {'type': 'medium', 'url': image_url_medium},
                                    {'type': "large", 'url': image_url_large}
                                ],
                                'certification':certification
                            },
                            'agreement':{
                                'amount':agreement[1],
                                'price':agreement[2],
                                'isBuy':False,
                                'canceled':agreement[3]
                            }
                        })

            except:
                continue

        # 3) 約定済一覧
        complete_list = []
        for account_address in request_json['account_address_list']:
            try:
                # 指定したアカウントアドレスから発生している約定イベント（買）を抽出する
                event_filter = ExchangeContract.events.SettlementOK.createFilter(
                    fromBlock='earliest',
                    argument_filters={'buyAddress': to_checksum_address(account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    order_id = entry['args']['orderId']
                    agreement_id = entry['args']['agreementId']
                    agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
                    # 決済済状態のもののみ以降の処理を実施
                    if agreement[4] == True:
                        token_address = to_checksum_address(entry['args']['tokenAddress'])
                        token_template = ListContract.functions.getTokenByAddress(token_address).call()
                        if token_template[0] == '0x0000000000000000000000000000000000000000':
                            continue

                        # Token-Contractへの接続
                        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

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

                        complete_list.append({
                            'token':{
                                'token_address': token_address,
                                'token_template': token_template[1],
                                'company_name': company_name,
                                'name':name,
                                'symbol':symbol,
                                'totalSupply':totalSupply,
                                'faceValue':faceValue,
                                'interestRate':interestRate,
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
                                'redemptionDate':redemptionDate,
                                'redemptionAmount':redemptionAmount,
                                'returnDate':returnDate,
                                'returnAmount':returnAmount,
                                'purpose':purpose,
                                'image_url': [
                                    {'type': 'small', 'url': image_url_small},
                                    {'type': 'medium', 'url': image_url_medium},
                                    {'type': "large", 'url': image_url_large}
                                ],
                                'certification':certification
                            },
                            'agreement':{
                                'order_id':order_id,
                                'agreementId':agreement_id,
                                'amount':agreement[1],
                                'price':agreement[2],
                                'isBuy':True
                            }
                        })

                # 指定したアカウントアドレスから発生している約定イベント（売）を抽出する
                event_filter = ExchangeContract.events.Agree.createFilter(
                    fromBlock='earliest',
                    argument_filters={'sellAddress': to_checksum_address(account_address)}
                )
                entries = event_filter.get_all_entries()
                web3.eth.uninstallFilter(event_filter.filter_id)

                for entry in entries:
                    order_id = entry['args']['orderId']
                    agreement_id = entry['args']['agreementId']
                    agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
                    # 未決済状態のもののみ以降の処理を実施
                    if agreement[4] == True:
                        token_address = to_checksum_address(entry['args']['tokenAddress'])
                        token_template = ListContract.functions.getTokenByAddress(token_address).call()
                        if token_template[0] == '0x0000000000000000000000000000000000000000':
                            continue

                        # Token-Contractへの接続
                        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

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

                        complete_list.append({
                            'token':{
                                'token_address': token_address,
                                'token_template': token_template[1],
                                'company_name': company_name,
                                'name':name,
                                'symbol':symbol,
                                'totalSupply':totalSupply,
                                'faceValue':faceValue,
                                'interestRate':interestRate,
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
                                'redemptionDate':redemptionDate,
                                'redemptionAmount':redemptionAmount,
                                'returnDate':returnDate,
                                'returnAmount':returnAmount,
                                'purpose':purpose,
                                'image_url': [
                                    {'type': 'small', 'url': image_url_small},
                                    {'type': 'medium', 'url': image_url_medium},
                                    {'type': "large", 'url': image_url_large}
                                ],
                                'certification':certification
                            },
                            'agreement':{
                                'order_id':order_id,
                                'agreementId':agreement_id,
                                'amount':agreement[1],
                                'price':agreement[2],
                                'isBuy':False
                            }
                        })

            except:
                continue

        response_json = {
            'order_list': order_list,
            'settlement_list':settlement_list,
            'complete_list':complete_list
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
