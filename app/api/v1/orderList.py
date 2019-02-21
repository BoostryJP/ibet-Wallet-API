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
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Order, Agreement, AgreementStatus

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
        session = req.context['session']

        request_json = OrderList.validate(req)

        # 企業リストの情報を取得する
        company_list = []
        if config.APP_ENV == 'local':
            company_list = json.load(open('data/company_list.json' , 'r'))
        else:
            try:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
            except:
                pass

        '''
        1) 注文一覧（order_list）
        '''
        order_list = []
        for account_address in request_json['account_address_list']:
            # 普通社債トークン
            order_list.extend(
                OrderList.get_StraightBond_OrderList(
                    session, account_address, company_list))

            # 会員権トークン
            order_list.extend(
                OrderList.get_Membership_OrderList(
                    session, account_address, company_list))

            # クーポントークン
            order_list.extend(
                OrderList.get_Coupon_OrderList(
                    session, account_address, company_list))

            order_list = sorted(
                order_list,
                key=lambda x:x['sort_id']
            )

        '''
        2) 決済中一覧（settlement_list）
        '''
        settlement_list = []
        for account_address in request_json['account_address_list']:
            # 普通社債トークン（買）
            settlement_list.extend(
                OrderList.get_StraightBond_SettlementList_Buy(
                    session, account_address, company_list))

            # 普通社債トークン（売）
            settlement_list.extend(
                OrderList.get_StraightBond_SettlementList_Sell(
                    session, account_address, company_list))

            # 会員権トークン（買）
            settlement_list.extend(
                OrderList.get_Membership_SettlementList_Buy(
                    session, account_address, company_list))

            # 会員権トークン（売）
            settlement_list.extend(
                OrderList.get_Membership_SettlementList_Sell(
                    session, account_address, company_list))

            # クーポントークン（買）
            settlement_list.extend(
                OrderList.get_Coupon_SettlementList_Buy(
                    session, account_address, company_list))

            # クーポントークン（売）
            settlement_list.extend(
                OrderList.get_Coupon_SettlementList_Sell(
                    session, account_address, company_list))

            settlement_list = sorted(
                settlement_list,
                key=lambda x:x['sort_id']
            )

        '''
        3) 約定済一覧（complete_list）
        '''
        complete_list = []
        for account_address in request_json['account_address_list']:
            # 普通社債トークン（買）
            complete_list.extend(
                OrderList.get_StraightBond_CompleteList_Buy(
                    session, account_address, company_list))

            # 普通社債トークン（売）
            complete_list.extend(
                OrderList.get_StraightBond_CompleteList_Sell(
                    session, account_address, company_list))

            # 会員権トークン（買）
            complete_list.extend(
                OrderList.get_Membership_CompleteList_Buy(
                    session, account_address, company_list))

            # 会員権トークン（売）
            complete_list.extend(
                OrderList.get_Membership_CompleteList_Sell(
                    session, account_address, company_list))

            # クーポントークン（買）
            complete_list.extend(
                OrderList.get_Coupon_CompleteList_Buy(
                    session, account_address, company_list))

            # クーポントークン（売）
            complete_list.extend(
                OrderList.get_Coupon_CompleteList_Sell(
                    session, account_address, company_list))

            complete_list = sorted(
                complete_list,
                key=lambda x:x['sort_id']
            )

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

    # 注文一覧：普通社債トークン
    @staticmethod
    def get_StraightBond_OrderList(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id).\
            filter(Order.exchange_address == exchange_address).\
            filter(Order.is_cancelled == False).\
            filter(Order.account_address == account_address).\
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])

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
                # NOTE:現状項目未使用であるため空のリストを返す
                certification = []

                order_list.append({
                    'token':{
                        'token_address': token_address,
                        'token_template': 'IbetStraightBond',
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
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧：会員権トークン
    @staticmethod
    def get_Membership_OrderList(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id).\
            filter(Order.exchange_address == exchange_address).\
            filter(Order.is_cancelled == False).\
            filter(Order.account_address == account_address).\
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])

                # Token-Contractへの接続
                TokenContract = Contract.get_contract('IbetMembership', token_address)

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

                image_url_s = TokenContract.functions.image_urls(0).call()
                image_url_m = TokenContract.functions.image_urls(1).call()
                image_url_l = TokenContract.functions.image_urls(2).call()

                owner_address = TokenContract.functions.owner().call()

                # 企業リストから、企業名を取得する
                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                order_list.append({
                    'token':{
                        'token_address': token_address,
                        'token_template': 'IbetMembership',
                        'company_name': company_name,
                        'name':name,
                        'symbol':symbol,
                        'total_supply':totalSupply,
                        'details':details,
                        'return_details':returnDetails,
                        'expiration_date':expirationDate,
                        'memo':memo,
                        'transferable':transferable,
                        'status':status,
                        'image_url': [
                            {'type': 'small', 'url': image_url_s},
                            {'type': 'medium', 'url': image_url_m},
                            {'type': "large", 'url': image_url_l}
                        ],
                    },
                    'order':{
                        'order_id':order_id,
                        'amount':orderBook[2],
                        'price':orderBook[3],
                        'isBuy':orderBook[4],
                        'canceled':orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧：クーポントークン
    @staticmethod
    def get_Coupon_OrderList(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id).\
            filter(Order.exchange_address == exchange_address).\
            filter(Order.is_cancelled == False).\
            filter(Order.account_address == account_address).\
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])

                # Token-Contractへの接続
                TokenContract = Contract.get_contract('IbetCoupon', token_address)

                # Token-Contractから情報を取得する
                name = TokenContract.functions.name().call()
                symbol = TokenContract.functions.symbol().call()
                totalSupply = TokenContract.functions.totalSupply().call()
                details = TokenContract.functions.details().call()
                expirationDate = TokenContract.functions.expirationDate().call()
                memo = TokenContract.functions.memo().call()
                transferable = TokenContract.functions.transferable().call()
                isValid = TokenContract.functions.isValid().call()

                image_url_s = TokenContract.functions.image_urls(0).call()
                image_url_m = TokenContract.functions.image_urls(1).call()
                image_url_l = TokenContract.functions.image_urls(2).call()

                owner_address = TokenContract.functions.owner().call()

                # 企業リストから、企業名を取得する
                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                order_list.append({
                    'token':{
                        'token_address': token_address,
                        'token_template': 'IbetCoupon',
                        'company_name': company_name,
                        'name':name,
                        'symbol':symbol,
                        'total_supply':totalSupply,
                        'details':details,
                        'expiration_date':expirationDate,
                        'memo':memo,
                        'transferable':transferable,
                        'is_valid':isValid,
                        'image_url': [
                            {'type': 'small', 'url': image_url_s},
                            {'type': 'medium', 'url': image_url_m},
                            {'type': "large", 'url': image_url_l}
                        ],
                    },
                    'order':{
                        'order_id':order_id,
                        'amount':orderBook[2],
                        'price':orderBook[3],
                        'isBuy':orderBook[4],
                        'canceled':orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 決済中一覧：普通社債トークン（買）
    @staticmethod
    def get_StraightBond_SettlementList_Buy(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.buyer_address == account_address).\
            filter(Agreement.status == AgreementStatus.PENDING.value).\
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

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
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            settlement_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetStraightBond',
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
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':True,
                    'canceled':agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：普通社債トークン（売）
    @staticmethod
    def get_StraightBond_SettlementList_Sell(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.seller_address == account_address).\
            filter(Agreement.status == AgreementStatus.PENDING.value).\
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

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
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            settlement_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetStraightBond',
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
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':False,
                    'canceled':agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：会員権トークン（買）
    @staticmethod
    def get_Membership_SettlementList_Buy(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.buyer_address == account_address).\
            filter(Agreement.status == AgreementStatus.PENDING.value).\
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            settlement_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetMembership',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'return_details':returnDetails,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'status':status,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':True,
                    'canceled':agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：会員権トークン（売）
    @staticmethod
    def get_Membership_SettlementList_Sell(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.seller_address == account_address).\
            filter(Agreement.status == AgreementStatus.PENDING.value).\
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            settlement_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetMembership',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'return_details':returnDetails,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'status':status,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':False,
                    'canceled':agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：クーポントークン（買）
    @staticmethod
    def get_Coupon_SettlementList_Buy(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.buyer_address == account_address).\
            filter(Agreement.status == AgreementStatus.PENDING.value).\
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            totalSupply = TokenContract.functions.totalSupply().call()
            details = TokenContract.functions.details().call()
            expirationDate = TokenContract.functions.expirationDate().call()
            memo = TokenContract.functions.memo().call()
            transferable = TokenContract.functions.transferable().call()
            isValid = TokenContract.functions.isValid().call()

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            settlement_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetCoupon',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'is_valid':isValid,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':True,
                    'canceled':agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：クーポントークン（売）
    @staticmethod
    def get_Coupon_SettlementList_Sell(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.seller_address == account_address).\
            filter(Agreement.status == AgreementStatus.PENDING.value).\
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            totalSupply = TokenContract.functions.totalSupply().call()
            details = TokenContract.functions.details().call()
            expirationDate = TokenContract.functions.expirationDate().call()
            memo = TokenContract.functions.memo().call()
            transferable = TokenContract.functions.transferable().call()
            isValid = TokenContract.functions.isValid().call()

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            settlement_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetCoupon',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'is_valid':isValid,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':False,
                    'canceled':agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 約定済一覧：普通社債トークン（買）
    @staticmethod
    def get_StraightBond_CompleteList_Buy(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.buyer_address == account_address).\
            filter(Agreement.status == AgreementStatus.DONE.value).\
            all()

        complete_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

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
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            complete_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetStraightBond',
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
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':True
                },
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：普通社債トークン（売）
    @staticmethod
    def get_StraightBond_CompleteList_Sell(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.seller_address == account_address).\
            filter(Agreement.status == AgreementStatus.DONE.value).\
            all()

        complete_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

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
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            complete_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetStraightBond',
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
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':False
                },
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：会員権トークン（買）
    @staticmethod
    def get_Membership_CompleteList_Buy(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.buyer_address == account_address).\
            filter(Agreement.status == AgreementStatus.DONE.value).\
            all()

        complete_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            complete_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetMembership',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'return_details':returnDetails,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'status':status,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':True
                },
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：会員権トークン（売）
    @staticmethod
    def get_Membership_CompleteList_Sell(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.seller_address == account_address).\
            filter(Agreement.status == AgreementStatus.DONE.value).\
            all()

        complete_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            complete_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetMembership',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'return_details':returnDetails,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'status':status,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':False
                },
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：クーポントークン（買）
    @staticmethod
    def get_Coupon_CompleteList_Buy(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.buyer_address == account_address).\
            filter(Agreement.status == AgreementStatus.DONE.value).\
            all()

        complete_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            totalSupply = TokenContract.functions.totalSupply().call()
            details = TokenContract.functions.details().call()
            expirationDate = TokenContract.functions.expirationDate().call()
            memo = TokenContract.functions.memo().call()
            transferable = TokenContract.functions.transferable().call()
            isValid = TokenContract.functions.isValid().call()

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            complete_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetCoupon',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'is_valid':isValid,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':True
                },
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：クーポントークン（売）
    @staticmethod
    def get_Coupon_CompleteList_Sell(session, account_address, company_list):
        exchange_address = to_checksum_address(
            os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'))

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id).\
            filter(Agreement.exchange_address == exchange_address).\
            filter(Agreement.seller_address == account_address).\
            filter(Agreement.status == AgreementStatus.DONE.value).\
            all()

        complete_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.orderBook(order_id).call()
            agreement = ExchangeContract.functions.agreements(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            totalSupply = TokenContract.functions.totalSupply().call()
            details = TokenContract.functions.details().call()
            expirationDate = TokenContract.functions.expirationDate().call()
            memo = TokenContract.functions.memo().call()
            transferable = TokenContract.functions.transferable().call()
            isValid = TokenContract.functions.isValid().call()

            image_url_s = TokenContract.functions.image_urls(0).call()
            image_url_m = TokenContract.functions.image_urls(1).call()
            image_url_l = TokenContract.functions.image_urls(2).call()

            owner_address = TokenContract.functions.owner().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            complete_list.append({
                'token':{
                    'token_address': token_address,
                    'token_template': 'IbetCoupon',
                    'company_name': company_name,
                    'name':name,
                    'symbol':symbol,
                    'total_supply':totalSupply,
                    'details':details,
                    'expiration_date':expirationDate,
                    'memo':memo,
                    'transferable':transferable,
                    'is_valid':isValid,
                    'image_url': [
                        {'type': 'small', 'url': image_url_s},
                        {'type': 'medium', 'url': image_url_m},
                        {'type': "large", 'url': image_url_l}
                    ],
                },
                'agreement':{
                    'exchange_address': exchange_address,
                    'order_id':order_id,
                    'agreementId':agreement_id,
                    'amount':agreement[1],
                    'price':agreement[2],
                    'isBuy':False
                },
                'sort_id': id
            })

        return complete_list
