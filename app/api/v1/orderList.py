# -*- coding: utf-8 -*-
import json
import requests
import os

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import TokenTemplate
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

# ------------------------------
# 注文一覧・約定一覧
# ------------------------------
class OrderList(BaseResource):
    '''
    Handle for endpoint: /v1/OrderList/
    '''
    def on_post(self, req, res):
        LOG.info('v1.OrderList.OrderList')
        session = req.context['session']

        request_json = OrderList.validate(req)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        # Exchange Contract
        exchange_contract_address = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        exchange_contract_abi = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)
        ExchangeContract = web3.eth.contract(
            address = to_checksum_address(exchange_contract_address),
            abi = exchange_contract_abi,
        )

        # TokenList Contract
        list_contract_address = config.TOKEN_LIST_CONTRACT_ADDRESS
        list_contract_abi = json.loads(config.TOKEN_LIST_CONTRACT_ABI)
        ListContract = web3.eth.contract(
            address = to_checksum_address(list_contract_address),
            abi = list_contract_abi,
        )

        try:
            company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            company_list = []

        # 1) 注文一覧
        order_list = []
        for account_address in request_json['account_address_list']:
            try:
                # 指定したアカウントアドレスから発生している注文イベントを抽出する
                event_filter = ExchangeContract.eventFilter(
                    'NewOrder', {
                        'filter':{'accountAddress':to_checksum_address(account_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter.get_all_entries()
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
                        abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                        token_abi = json.loads(abi_str)
                        TokenContract = web3.eth.contract(
                            address = token_address,
                            abi = token_abi
                        )

                        # Token-Contractから情報を取得する
                        name = TokenContract.functions.name().call()
                        symbol = TokenContract.functions.symbol().call()
                        totalSupply = TokenContract.functions.totalSupply().call()
                        faceValue = TokenContract.functions.faceValue().call()
                        interestRate = TokenContract.functions.interestRate().call()

                        interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()
                        interestPaymentDate = json.loads(
                            interestPaymentDate_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                        interestPaymentDate1 = ''
                        interestPaymentDate2 = ''
                        if 'interestPaymentDate1' in interestPaymentDate:
                            interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                        if 'interestPaymentDate2' in interestPaymentDate:
                            interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']

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
                        event_filter = TokenContract.eventFilter(
                            'Sign', {
                                'filter':{},
                                'fromBlock':'earliest'
                            }
                        )
                        try:
                            entries = event_filter.get_all_entries()
                        except:
                            entries = []

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
                event_filter_buy = ExchangeContract.eventFilter(
                    'Agree', {
                        'filter':{'buyAddress':to_checksum_address(account_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter_buy.get_all_entries()

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
                        abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                        token_abi = json.loads(abi_str)
                        TokenContract = web3.eth.contract(
                            address = token_address,
                            abi = token_abi
                        )

                        # Token-Contractから情報を取得する
                        name = TokenContract.functions.name().call()
                        symbol = TokenContract.functions.symbol().call()
                        totalSupply = TokenContract.functions.totalSupply().call()
                        faceValue = TokenContract.functions.faceValue().call()
                        interestRate = TokenContract.functions.interestRate().call()

                        interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()
                        interestPaymentDate = json.loads(
                            interestPaymentDate_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                        interestPaymentDate1 = ''
                        interestPaymentDate2 = ''
                        if 'interestPaymentDate1' in interestPaymentDate:
                            interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                        if 'interestPaymentDate2' in interestPaymentDate:
                            interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']

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
                        event_filter = TokenContract.eventFilter(
                            'Sign', {
                                'filter':{},
                                'fromBlock':'earliest'
                            }
                        )
                        try:
                            entries = event_filter.get_all_entries()
                        except:
                            entries = []

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
                event_filter_sell = ExchangeContract.eventFilter(
                    'Agree', {
                        'filter':{'sellAddress':to_checksum_address(account_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter_sell.get_all_entries()

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
                        abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                        token_abi = json.loads(abi_str)
                        TokenContract = web3.eth.contract(
                            address = token_address,
                            abi = token_abi
                        )

                        # Token-Contractから情報を取得する
                        name = TokenContract.functions.name().call()
                        symbol = TokenContract.functions.symbol().call()
                        totalSupply = TokenContract.functions.totalSupply().call()
                        faceValue = TokenContract.functions.faceValue().call()
                        interestRate = TokenContract.functions.interestRate().call()

                        interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()
                        interestPaymentDate = json.loads(
                            interestPaymentDate_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                        interestPaymentDate1 = ''
                        interestPaymentDate2 = ''
                        if 'interestPaymentDate1' in interestPaymentDate:
                            interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                        if 'interestPaymentDate2' in interestPaymentDate:
                            interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']

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
                        event_filter = TokenContract.eventFilter(
                            'Sign', {
                                'filter':{},
                                'fromBlock':'earliest'
                            }
                        )
                        try:
                            entries = event_filter.get_all_entries()
                        except:
                            entries = []

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
                event_filter_buy = ExchangeContract.eventFilter(
                    'SettlementOK', {
                        'filter':{'buyAddress':to_checksum_address(account_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter_buy.get_all_entries()

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
                        abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                        token_abi = json.loads(abi_str)
                        TokenContract = web3.eth.contract(
                            address = token_address,
                            abi = token_abi
                        )

                        # Token-Contractから情報を取得する
                        name = TokenContract.functions.name().call()
                        symbol = TokenContract.functions.symbol().call()
                        totalSupply = TokenContract.functions.totalSupply().call()
                        faceValue = TokenContract.functions.faceValue().call()
                        interestRate = TokenContract.functions.interestRate().call()

                        interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()
                        interestPaymentDate = json.loads(
                            interestPaymentDate_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                        interestPaymentDate1 = ''
                        interestPaymentDate2 = ''
                        if 'interestPaymentDate1' in interestPaymentDate:
                            interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                        if 'interestPaymentDate2' in interestPaymentDate:
                            interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']

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
                        event_filter = TokenContract.eventFilter(
                            'Sign', {
                                'filter':{},
                                'fromBlock':'earliest'
                            }
                        )
                        try:
                            entries = event_filter.get_all_entries()
                        except:
                            entries = []

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
                event_filter_sell = ExchangeContract.eventFilter(
                    'Agree', {
                        'filter':{'sellAddress':to_checksum_address(account_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter_sell.get_all_entries()

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
                        abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                        token_abi = json.loads(abi_str)
                        TokenContract = web3.eth.contract(
                            address = token_address,
                            abi = token_abi
                        )

                        # Token-Contractから情報を取得する
                        name = TokenContract.functions.name().call()
                        symbol = TokenContract.functions.symbol().call()
                        totalSupply = TokenContract.functions.totalSupply().call()
                        faceValue = TokenContract.functions.faceValue().call()
                        interestRate = TokenContract.functions.interestRate().call()

                        interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()
                        interestPaymentDate = json.loads(
                            interestPaymentDate_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                        interestPaymentDate1 = ''
                        interestPaymentDate2 = ''
                        if 'interestPaymentDate1' in interestPaymentDate:
                            interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                        if 'interestPaymentDate2' in interestPaymentDate:
                            interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']

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
                        event_filter = TokenContract.eventFilter(
                            'Sign', {
                                'filter':{},
                                'fromBlock':'earliest'
                            }
                        )
                        try:
                            entries = event_filter.get_all_entries()
                        except:
                            entries = []

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
