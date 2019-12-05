# -*- coding: utf-8 -*-
import json
import requests

from cerberus import Validator
from datetime import timedelta, timezone

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.contracts import Contract
from app.model import Order, Agreement, AgreementStatus, Listing, \
    BondToken, MembershipToken, CouponToken

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


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
            company_list = json.load(open('data/company_list.json', 'r'))
        else:
            try:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
            except:
                pass

        # Listingの情報を取得する
        available_tokens = session.query(Listing).all()

        '''
        1) 注文一覧（order_list）
        '''
        order_list = []
        for account_address in request_json['account_address_list']:
            # BOND
            if config.BOND_TOKEN_ENABLED is True:
                try:
                    order_list.extend(
                        OrderList.get_StraightBond_OrderList(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            # MEMBERSHIP
            if config.MEMBERSHIP_TOKEN_ENABLED is True:
                try:
                    order_list.extend(
                        OrderList.get_Membership_OrderList(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            # COUPON
            if config.COUPON_TOKEN_ENABLED is True:
                try:
                    order_list.extend(
                        OrderList.get_Coupon_OrderList(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            order_list = sorted(
                order_list,
                key=lambda x: x['sort_id']
            )

        '''
        2) 決済中一覧（settlement_list）
        '''
        settlement_list = []
        for account_address in request_json['account_address_list']:
            # BOND
            if config.BOND_TOKEN_ENABLED is True:
                # BOND_BUY
                try:
                    settlement_list.extend(
                        OrderList.get_StraightBond_SettlementList_Buy(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

                # BOND_SELL
                try:
                    settlement_list.extend(
                        OrderList.get_StraightBond_SettlementList_Sell(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            # MEMBERSHIP
            if config.MEMBERSHIP_TOKEN_ENABLED is True:
                # MEMBERSHIP_BUY
                try:
                    settlement_list.extend(
                        OrderList.get_Membership_SettlementList_Buy(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

                # MEMBERSHIP_SELL
                try:
                    settlement_list.extend(
                        OrderList.get_Membership_SettlementList_Sell(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            # COUPON
            if config.COUPON_TOKEN_ENABLED is True:
                # COUPON_BUY
                try:
                    settlement_list.extend(
                        OrderList.get_Coupon_SettlementList_Buy(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

                # COUPON_SELL
                try:
                    settlement_list.extend(
                        OrderList.get_Coupon_SettlementList_Sell(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            settlement_list = sorted(
                settlement_list,
                key=lambda x: x['sort_id']
            )

        '''
        3) 約定済一覧（complete_list）
        '''
        complete_list = []
        for account_address in request_json['account_address_list']:
            # BOND
            if config.BOND_TOKEN_ENABLED is True:
                # BOND_BUY
                try:
                    complete_list.extend(
                        OrderList.get_StraightBond_CompleteList_Buy(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

                # BOND_SELL
                try:
                    complete_list.extend(
                        OrderList.get_StraightBond_CompleteList_Sell(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            # MEMBERSHIP
            if config.MEMBERSHIP_TOKEN_ENABLED is True:
                # MEMBERSHIP_BUY
                try:
                    complete_list.extend(
                        OrderList.get_Membership_CompleteList_Buy(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

                # MEMBERSHIP_SELL
                try:
                    complete_list.extend(
                        OrderList.get_Membership_CompleteList_Sell(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            # COUPON
            if config.COUPON_TOKEN_ENABLED is True:
                # COUPON_BUY
                try:
                    complete_list.extend(
                        OrderList.get_Coupon_CompleteList_Buy(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

                # COUPON_SELL
                try:
                    complete_list.extend(
                        OrderList.get_Coupon_CompleteList_Sell(
                            session, account_address, company_list, available_tokens))
                except Exception as err:
                    LOG.error(err)
                    pass

            complete_list = sorted(
                complete_list,
                key=lambda x: x['sort_id']
            )

        response_json = {
            'order_list': order_list,
            'settlement_list': settlement_list,
            'complete_list': complete_list
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
    def get_StraightBond_OrderList(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract('IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])

                # Token-Contractへの接続
                TokenContract = Contract.get_contract('IbetStraightBond', token_address)

                # Token-Contractから情報を取得する
                name = TokenContract.functions.name().call()
                symbol = TokenContract.functions.symbol().call()
                total_supply = TokenContract.functions.totalSupply().call()
                face_value = TokenContract.functions.faceValue().call()
                interest_rate = TokenContract.functions.interestRate().call()

                interest_payment_date_string = TokenContract.functions.interestPaymentDate().call()

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
                        interest_payment_date_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))
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
                except:
                    pass

                redemption_date = TokenContract.functions.redemptionDate().call()
                redemption_amount = TokenContract.functions.redemptionAmount().call()
                return_date = TokenContract.functions.returnDate().call()
                return_amount = TokenContract.functions.returnAmount().call()
                purpose = TokenContract.functions.purpose().call()
                image_url_1 = TokenContract.functions.getImageURL(0).call()
                image_url_2 = TokenContract.functions.getImageURL(1).call()
                image_url_3 = TokenContract.functions.getImageURL(2).call()
                owner_address = TokenContract.functions.owner().call()
                contact_information = TokenContract.functions.contactInformation().call()
                privacy_policy = TokenContract.functions.privacyPolicy().call()

                # 企業リストから、企業名を取得する
                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                # 許可済みトークンリストから、token情報を取得する
                available_token = {}
                for available in available_tokens:
                    if to_checksum_address(available.token_address) == token_address:
                        available_token = available

                # 第三者認定（Sign）のイベント情報を検索する
                # NOTE:現状項目未使用であるため空のリストを返す
                certification = []
                bondtoken = BondToken()
                bondtoken.token_address = token_address
                bondtoken.token_template = 'IbetStraightBond'
                bondtoken.company_name = company_name
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
                # 許可済みトークンに存在しない場合は、決済手段はFalseとする
                bondtoken.payment_method_credit_card = available_token.payment_method_credit_card \
                    if hasattr(available_token, "payment_method_credit_card") else False
                bondtoken.payment_method_bank = available_token.payment_method_bank \
                    if hasattr(available_token, "payment_method_bank") else False
                bondtoken.contact_information = contact_information
                bondtoken.privacy_policy = privacy_policy

                order_list.append({
                    'token': bondtoken.__dict__,
                    'order': {
                        'order_id': order_id,
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧：会員権トークン
    @staticmethod
    def get_Membership_OrderList(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])

                # Token-Contractへの接続
                TokenContract = Contract.get_contract('IbetMembership', token_address)

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
                contact_information = TokenContract.functions.contactInformation().call()
                privacy_policy = TokenContract.functions.privacyPolicy().call()

                owner_address = TokenContract.functions.owner().call()

                # 企業リストから、企業名を取得する
                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                # 許可済みトークンリストから、token情報を取得する
                available_token = {}
                for available in available_tokens:
                    if to_checksum_address(available.token_address) == token_address:
                        available_token = available

                membershiptoken = MembershipToken()
                membershiptoken.token_address = token_address
                membershiptoken.token_template = 'IbetMembership'
                membershiptoken.company_name = company_name
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
                membershiptoken.payment_method_credit_card = available_token.payment_method_credit_card \
                    if hasattr(available_token, "payment_method_credit_card") else False
                membershiptoken.payment_method_bank = available_token.payment_method_bank \
                    if hasattr(available_token, "payment_method_bank") else False
                membershiptoken.contact_information = contact_information
                membershiptoken.privacy_policy = privacy_policy

                order_list.append({
                    'token': membershiptoken.__dict__,
                    'order': {
                        'order_id': order_id,
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 注文一覧：クーポントークン
    @staticmethod
    def get_Coupon_OrderList(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している注文イベントを抽出する
        entries = session.query(Order.id, Order.order_id). \
            filter(Order.exchange_address == exchange_address). \
            filter(Order.is_cancelled == False). \
            filter(Order.account_address == account_address). \
            all()

        order_list = []
        for (id, order_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()

            # 残注文ゼロの場合は以下の処理をSKIP
            if orderBook[2] != 0:
                token_address = to_checksum_address(orderBook[1])

                # Token-Contractへの接続
                TokenContract = Contract.get_contract('IbetCoupon', token_address)

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
                contact_information = TokenContract.functions.contactInformation().call()
                privacy_policy = TokenContract.functions.privacyPolicy().call()

                owner_address = TokenContract.functions.owner().call()

                # 企業リストから、企業名を取得する
                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                # 許可済みトークンリストから、token情報を取得する
                available_token = {}
                for available in available_tokens:
                    if to_checksum_address(available.token_address) == token_address:
                        available_token = available

                coupontoken = CouponToken()
                coupontoken.token_address = token_address
                coupontoken.token_template = 'IbetCoupon'
                coupontoken.company_name = company_name
                coupontoken.name = name
                coupontoken.symbol = symbol
                coupontoken.total_supply = total_supply
                coupontoken.details = details
                coupontoken.return_details = return_details
                coupontoken.expiration_date = expiration_date
                coupontoken.memo = memo
                coupontoken.transferable = transferable
                coupontoken.status = status
                coupontoken.image_url = [
                    {'id': 1, 'url': image_url_1},
                    {'id': 2, 'url': image_url_2},
                    {'id': 3, 'url': image_url_3}
                ]
                coupontoken.payment_method_credit_card = available_token.payment_method_credit_card \
                    if hasattr(available_token, "payment_method_credit_card") else False
                coupontoken.payment_method_bank = available_token.payment_method_bank \
                    if hasattr(available_token, "payment_method_bank") else False
                coupontoken.contact_information = contact_information
                coupontoken.privacy_policy = privacy_policy

                order_list.append({
                    'token': coupontoken.__dict__,
                    'order': {
                        'order_id': order_id,
                        'amount': orderBook[2],
                        'price': orderBook[3],
                        'is_buy': orderBook[4],
                        'canceled': orderBook[6]
                    },
                    'sort_id': id
                })

        return order_list

    # 決済中一覧：普通社債トークン（買）
    @staticmethod
    def get_StraightBond_SettlementList_Buy(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetStraightBond', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            total_supply = TokenContract.functions.totalSupply().call()
            face_value = TokenContract.functions.faceValue().call()
            interest_rate = TokenContract.functions.interestRate().call()

            interest_payment_date_string = TokenContract.functions.interestPaymentDate().call()

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
                    interest_payment_date_string.replace("'", '"'). \
                        replace('True', 'true').replace('False', 'false'))
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
            except:
                pass

            redemption_date = TokenContract.functions.redemptionDate().call()
            redemption_amount = TokenContract.functions.redemptionAmount().call()
            return_date = TokenContract.functions.returnDate().call()
            return_amount = TokenContract.functions.returnAmount().call()
            purpose = TokenContract.functions.purpose().call()
            image_url_1 = TokenContract.functions.getImageURL(0).call()
            image_url_2 = TokenContract.functions.getImageURL(1).call()
            image_url_3 = TokenContract.functions.getImageURL(2).call()
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            # 第三者認定（Sign）のイベント情報を検索する
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            bondtoken = BondToken()
            bondtoken.token_address = token_address
            bondtoken.token_template = 'IbetStraightBond'
            bondtoken.company_name = company_name
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
            # 許可済みトークンに存在しない場合は、決済手段はFalseとする
            bondtoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            bondtoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            bondtoken.contact_information = contact_information
            bondtoken.privacy_policy = privacy_policy

            settlement_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：普通社債トークン（売）
    @staticmethod
    def get_StraightBond_SettlementList_Sell(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetStraightBond', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            total_supply = TokenContract.functions.totalSupply().call()
            face_value = TokenContract.functions.faceValue().call()
            interest_rate = TokenContract.functions.interestRate().call()

            interest_payment_date_string = TokenContract.functions.interestPaymentDate().call()

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
                    interest_payment_date_string.replace("'", '"'). \
                        replace('True', 'true').replace('False', 'false'))
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
            except:
                pass

            redemption_date = TokenContract.functions.redemptionDate().call()
            redemption_amount = TokenContract.functions.redemptionAmount().call()
            return_date = TokenContract.functions.returnDate().call()
            return_amount = TokenContract.functions.returnAmount().call()
            purpose = TokenContract.functions.purpose().call()
            image_url_1 = TokenContract.functions.getImageURL(0).call()
            image_url_2 = TokenContract.functions.getImageURL(1).call()
            image_url_3 = TokenContract.functions.getImageURL(2).call()
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']
            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            # 第三者認定（Sign）のイベント情報を検索する
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            bondtoken = BondToken()
            bondtoken.token_address = token_address
            bondtoken.token_template = 'IbetStraightBond'
            bondtoken.company_name = company_name
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
            # 許可済みトークンに存在しない場合は、決済手段はFalseとする
            bondtoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            bondtoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            bondtoken.contact_information = contact_information
            bondtoken.privacy_policy = privacy_policy

            settlement_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：会員権トークン（買）
    @staticmethod
    def get_Membership_SettlementList_Buy(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']
            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            membershiptoken = MembershipToken()
            membershiptoken.token_address = token_address
            membershiptoken.token_template = 'IbetMembership'
            membershiptoken.company_name = company_name
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
            membershiptoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            membershiptoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            membershiptoken.contact_information = contact_information
            membershiptoken.privacy_policy = privacy_policy

            settlement_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：会員権トークン（売）
    @staticmethod
    def get_Membership_SettlementList_Sell(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']
            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            membershiptoken = MembershipToken()
            membershiptoken.token_address = token_address
            membershiptoken.token_template = 'IbetMembership'
            membershiptoken.company_name = company_name
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
            membershiptoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            membershiptoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            membershiptoken.contact_information = contact_information
            membershiptoken.privacy_policy = privacy_policy

            settlement_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：クーポントークン（買）
    @staticmethod
    def get_Coupon_SettlementList_Buy(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            coupontoken = CouponToken()
            coupontoken.token_address = token_address
            coupontoken.token_template = 'IbetCoupon'
            coupontoken.company_name = company_name
            coupontoken.name = name
            coupontoken.symbol = symbol
            coupontoken.total_supply = total_supply
            coupontoken.details = details
            coupontoken.return_details = return_details
            coupontoken.expiration_date = expiration_date
            coupontoken.memo = memo
            coupontoken.transferable = transferable
            coupontoken.status = status
            coupontoken.image_url = [
                {'id': 1, 'url': image_url_1},
                {'id': 2, 'url': image_url_2},
                {'id': 3, 'url': image_url_3}
            ]
            coupontoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            coupontoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            coupontoken.contact_information = contact_information
            coupontoken.privacy_policy = privacy_policy

            settlement_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 決済中一覧：クーポントークン（売）
    @staticmethod
    def get_Coupon_SettlementList_Sell(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：未決済）を抽出する
        entries = session.query(Agreement.id, Agreement.order_id, Agreement.agreement_id). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.PENDING.value). \
            all()

        settlement_list = []
        for (id, order_id, agreement_id) in entries:
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            coupontoken = CouponToken()
            coupontoken.token_address = token_address
            coupontoken.token_template = 'IbetCoupon'
            coupontoken.company_name = company_name
            coupontoken.name = name
            coupontoken.symbol = symbol
            coupontoken.total_supply = total_supply
            coupontoken.details = details
            coupontoken.return_details = return_details
            coupontoken.expiration_date = expiration_date
            coupontoken.memo = memo
            coupontoken.transferable = transferable
            coupontoken.status = status
            coupontoken.image_url = [
                {'id': 1, 'url': image_url_1},
                {'id': 2, 'url': image_url_2},
                {'id': 3, 'url': image_url_3}
            ]
            coupontoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            coupontoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            coupontoken.contact_information = contact_information
            coupontoken.privacy_policy = privacy_policy

            settlement_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False,
                    'canceled': agreement[3]
                },
                'sort_id': id
            })

        return settlement_list

    # 約定済一覧：普通社債トークン（買）
    @staticmethod
    def get_StraightBond_CompleteList_Buy(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp. \
                    replace(tzinfo=UTC).astimezone(JST).strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetStraightBond', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            total_supply = TokenContract.functions.totalSupply().call()
            face_value = TokenContract.functions.faceValue().call()
            interest_rate = TokenContract.functions.interestRate().call()

            interest_payment_date_string = TokenContract.functions.interestPaymentDate().call()

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
                    interest_payment_date_string.replace("'", '"'). \
                        replace('True', 'true').replace('False', 'false'))
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
            except:
                pass

            redemption_date = TokenContract.functions.redemptionDate().call()
            redemption_amount = TokenContract.functions.redemptionAmount().call()
            return_date = TokenContract.functions.returnDate().call()
            return_amount = TokenContract.functions.returnAmount().call()
            purpose = TokenContract.functions.purpose().call()
            image_url_1 = TokenContract.functions.getImageURL(0).call()
            image_url_2 = TokenContract.functions.getImageURL(1).call()
            image_url_3 = TokenContract.functions.getImageURL(2).call()
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            # 第三者認定（Sign）のイベント情報を検索する
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            bondtoken = BondToken()
            bondtoken.token_address = token_address
            bondtoken.token_template = 'IbetStraightBond'
            bondtoken.company_name = company_name
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
            # 許可済みトークンに存在しない場合は、決済手段はFalseとする
            bondtoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            bondtoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            bondtoken.contact_information = contact_information
            bondtoken.privacy_policy = privacy_policy

            complete_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：普通社債トークン（売）
    @staticmethod
    def get_StraightBond_CompleteList_Sell(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp. \
                    replace(tzinfo=UTC).astimezone(JST).strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetStraightBond', token_address)

            # Token-Contractから情報を取得する
            name = TokenContract.functions.name().call()
            symbol = TokenContract.functions.symbol().call()
            total_supply = TokenContract.functions.totalSupply().call()
            face_value = TokenContract.functions.faceValue().call()
            interest_rate = TokenContract.functions.interestRate().call()

            interest_payment_date_string = TokenContract.functions.interestPaymentDate().call()

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
                    interest_payment_date_string.replace("'", '"'). \
                        replace('True', 'true').replace('False', 'false'))
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
            except:
                pass

            redemption_date = TokenContract.functions.redemptionDate().call()
            redemption_amount = TokenContract.functions.redemptionAmount().call()
            return_date = TokenContract.functions.returnDate().call()
            return_amount = TokenContract.functions.returnAmount().call()
            purpose = TokenContract.functions.purpose().call()
            image_url_1 = TokenContract.functions.getImageURL(0).call()
            image_url_2 = TokenContract.functions.getImageURL(1).call()
            image_url_3 = TokenContract.functions.getImageURL(2).call()
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            # 第三者認定（Sign）のイベント情報を検索する
            # NOTE:現状項目未使用であるため空のリストを返す
            certification = []

            bondtoken = BondToken()
            bondtoken.token_address = token_address
            bondtoken.token_template = 'IbetStraightBond'
            bondtoken.company_name = company_name
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
            # 許可済みトークンに存在しない場合は、決済手段はFalseとする
            bondtoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            bondtoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            bondtoken.contact_information = contact_information
            bondtoken.privacy_policy = privacy_policy

            complete_list.append({
                'token': bondtoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：会員権トークン（買）
    @staticmethod
    def get_Membership_CompleteList_Buy(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp. \
                    replace(tzinfo=UTC).astimezone(JST).strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']
            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            membershiptoken = MembershipToken()
            membershiptoken.token_address = token_address
            membershiptoken.token_template = 'IbetMembership'
            membershiptoken.company_name = company_name
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
            membershiptoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            membershiptoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            membershiptoken.contact_information = contact_information
            membershiptoken.privacy_policy = privacy_policy

            complete_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：会員権トークン（売）
    @staticmethod
    def get_Membership_CompleteList_Sell(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetMembershipExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（売：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp. \
                    replace(tzinfo=UTC).astimezone(JST).strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetMembership', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']
            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            membershiptoken = MembershipToken()
            membershiptoken.token_address = token_address
            membershiptoken.token_template = 'IbetMembership'
            membershiptoken.company_name = company_name
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
            membershiptoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            membershiptoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            membershiptoken.contact_information = contact_information
            membershiptoken.privacy_policy = privacy_policy

            complete_list.append({
                'token': membershiptoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：クーポントークン（買）
    @staticmethod
    def get_Coupon_CompleteList_Buy(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.buyer_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp. \
                    replace(tzinfo=UTC).astimezone(JST).strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            coupontoken = CouponToken()
            coupontoken.token_address = token_address
            coupontoken.token_template = 'IbetCoupon'
            coupontoken.company_name = company_name
            coupontoken.name = name
            coupontoken.symbol = symbol
            coupontoken.total_supply = total_supply
            coupontoken.details = details
            coupontoken.return_details = return_details
            coupontoken.expiration_date = expiration_date
            coupontoken.memo = memo
            coupontoken.transferable = transferable
            coupontoken.status = status
            coupontoken.image_url = [
                {'id': 1, 'url': image_url_1},
                {'id': 2, 'url': image_url_2},
                {'id': 3, 'url': image_url_3}
            ]
            coupontoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            coupontoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            coupontoken.contact_information = contact_information
            coupontoken.privacy_policy = privacy_policy

            complete_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': True
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list

    # 約定済一覧：クーポントークン（売）
    @staticmethod
    def get_Coupon_CompleteList_Sell(session, account_address, company_list, available_tokens):
        exchange_address = to_checksum_address(
            config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS)

        # Exchange Contract
        ExchangeContract = Contract.get_contract(
            'IbetCouponExchange', exchange_address)

        # 指定したアカウントアドレスから発生している約定イベント（買：決済済）を抽出する
        entries = session.query(
            Agreement.id,
            Agreement.order_id,
            Agreement.agreement_id,
            Agreement.settlement_timestamp). \
            filter(Agreement.exchange_address == exchange_address). \
            filter(Agreement.seller_address == account_address). \
            filter(Agreement.status == AgreementStatus.DONE.value). \
            all()

        complete_list = []
        for (id, order_id, agreement_id, settlement_timestamp) in entries:
            if settlement_timestamp is not None:
                settlement_timestamp_jp = settlement_timestamp. \
                    replace(tzinfo=UTC).astimezone(JST).strftime("%Y/%m/%d %H:%M:%S")
            else:
                settlement_timestamp_jp = ''
            orderBook = ExchangeContract.functions.getOrder(order_id).call()
            agreement = ExchangeContract.functions.getAgreement(order_id, agreement_id).call()
            token_address = to_checksum_address(orderBook[1])

            # Token-Contractへの接続
            TokenContract = Contract.get_contract('IbetCoupon', token_address)

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
            owner_address = TokenContract.functions.owner().call()
            contact_information = TokenContract.functions.contactInformation().call()
            privacy_policy = TokenContract.functions.privacyPolicy().call()

            # 企業リストから、企業名を取得する
            company_name = ''
            for company in company_list:
                if to_checksum_address(company['address']) == owner_address:
                    company_name = company['corporate_name']

            # 許可済みトークンリストから、token情報を取得する
            available_token = {}
            for available in available_tokens:
                if to_checksum_address(available.token_address) == token_address:
                    available_token = available

            coupontoken = CouponToken()
            coupontoken.token_address = token_address
            coupontoken.token_template = 'IbetCoupon'
            coupontoken.company_name = company_name
            coupontoken.name = name
            coupontoken.symbol = symbol
            coupontoken.total_supply = total_supply
            coupontoken.details = details
            coupontoken.return_details = return_details
            coupontoken.expiration_date = expiration_date
            coupontoken.memo = memo
            coupontoken.transferable = transferable
            coupontoken.status = status
            coupontoken.image_url = [
                {'id': 1, 'url': image_url_1},
                {'id': 2, 'url': image_url_2},
                {'id': 3, 'url': image_url_3}
            ]
            coupontoken.payment_method_credit_card = available_token.payment_method_credit_card \
                if hasattr(available_token, "payment_method_credit_card") else False
            coupontoken.payment_method_bank = available_token.payment_method_bank \
                if hasattr(available_token, "payment_method_bank") else False
            coupontoken.contact_information = contact_information
            coupontoken.privacy_policy = privacy_policy

            complete_list.append({
                'token': coupontoken.__dict__,
                'agreement': {
                    'exchange_address': exchange_address,
                    'order_id': order_id,
                    'agreement_id': agreement_id,
                    'amount': agreement[1],
                    'price': agreement[2],
                    'is_buy': False
                },
                'settlement_timestamp': settlement_timestamp_jp,
                'sort_id': id
            })

        return complete_list
