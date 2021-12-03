"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import json
from decimal import Decimal
from datetime import datetime, timedelta

from eth_utils import to_checksum_address

from app import config
from app import log
from app.contracts import Contract
from app.model.db import Listing
from app.utils.company_list import CompanyList

LOG = log.get_logger()


class TokenBase:
    token_address: str
    token_template: str
    owner_address: str
    company_name: str
    rsa_publickey: str
    name: str
    symbol: str
    total_supply: int
    tradable_exchange: str
    contact_information: str
    privacy_policy: str
    status: bool
    max_holding_quantity: int
    max_sell_amount: int


class BondToken(TokenBase):
    personal_info_address: str
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool
    face_value: int
    interest_rate: float
    interest_payment_date1: str
    interest_payment_date2: str
    interest_payment_date3: str
    interest_payment_date4: str
    interest_payment_date5: str
    interest_payment_date6: str
    interest_payment_date7: str
    interest_payment_date8: str
    interest_payment_date9: str
    interest_payment_date10: str
    interest_payment_date11: str
    interest_payment_date12: str
    redemption_date: str
    redemption_value: int
    return_date: str
    return_amount: str
    purpose: str
    memo: str
    is_redeemed: bool

    # トークン情報のキャッシュ
    cache = {}

    @staticmethod
    def get(session, token_address: str):
        """
        債券トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: BondToken
        """

        # IbetStraightBond コントラクトへの接続
        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

        # キャッシュを利用する場合
        if config.TOKEN_CACHE:
            if token_address in BondToken.cache:
                token_cache = BondToken.cache[token_address]
                if token_cache.get("expiration_datetime") > datetime.utcnow():
                    # キャッシュ情報を取得
                    bondtoken = token_cache["token"]
                    # キャッシュ情報以外の情報を取得
                    bondtoken.total_supply = TokenContract.functions.totalSupply().call()
                    bondtoken.transferable = TokenContract.functions.transferable().call()
                    bondtoken.is_offering = TokenContract.functions.isOffering().call()
                    bondtoken.status = TokenContract.functions.status().call()
                    bondtoken.is_redeemed = TokenContract.functions.isRedeemed().call()
                    return bondtoken

        # キャッシュ未利用の場合
        # または、キャッシュに情報が存在しない場合
        # または、キャッシュの有効期限が切れている場合

        # Contractから情報を取得する
        owner_address = TokenContract.functions.owner().call()
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
                interest_payment_date_string.replace("'", '"').replace('True', 'true').replace('False', 'false')
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
        except Exception as err:
            LOG.warning("Failed to load interestPaymentDate: ", err)

        redemption_date = TokenContract.functions.redemptionDate().call()
        redemption_value = TokenContract.functions.redemptionValue().call()
        return_date = TokenContract.functions.returnDate().call()
        return_amount = TokenContract.functions.returnAmount().call()
        purpose = TokenContract.functions.purpose().call()
        is_redeemed = TokenContract.functions.isRedeemed().call()
        transferable = TokenContract.functions.transferable().call()
        is_offering = TokenContract.functions.isOffering().call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()
        tradable_exchange = TokenContract.functions.tradableExchange().call()
        status = TokenContract.functions.status().call()
        memo = TokenContract.functions.memo().call()
        personal_info_address = TokenContract.functions.personalInfoAddress().call()
        transfer_approval_required = TokenContract.functions.transferApprovalRequired().call()

        # 企業リストから、企業名を取得する
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = session.query(Listing).filter(Listing.token_address == token_address).first()

        bondtoken = BondToken()
        bondtoken.token_address = token_address
        bondtoken.token_template = 'IbetStraightBond'
        bondtoken.owner_address = owner_address
        bondtoken.company_name = company_name
        bondtoken.rsa_publickey = rsa_publickey
        bondtoken.name = name
        bondtoken.symbol = symbol
        bondtoken.total_supply = total_supply
        bondtoken.tradable_exchange = tradable_exchange
        bondtoken.contact_information = contact_information
        bondtoken.privacy_policy = privacy_policy
        bondtoken.status = status
        bondtoken.max_holding_quantity = listed_token.max_holding_quantity \
            if hasattr(listed_token, "max_holding_quantity") else 0
        bondtoken.max_sell_amount = listed_token.max_sell_amount \
            if hasattr(listed_token, "max_sell_amount") else 0
        bondtoken.personal_info_address = personal_info_address
        bondtoken.transferable = transferable
        bondtoken.is_offering = is_offering
        bondtoken.transfer_approval_required = transfer_approval_required
        bondtoken.face_value = face_value
        bondtoken.interest_rate = float(Decimal(str(interest_rate)) * Decimal('0.0001'))
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
        bondtoken.redemption_value = redemption_value
        bondtoken.return_date = return_date
        bondtoken.return_amount = return_amount
        bondtoken.purpose = purpose
        bondtoken.memo = memo
        bondtoken.is_redeemed = is_redeemed

        if config.TOKEN_CACHE:
            BondToken.cache[token_address] = {
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=config.TOKEN_CACHE_TTL),
                "token": bondtoken
            }

        return bondtoken


class ShareToken(TokenBase):
    personal_info_address: str
    transferable: bool
    is_offering: bool
    transfer_approval_required: bool
    issue_price: int
    cancellation_date: str
    memo: str
    principal_value: int
    is_canceled: bool
    dividend_information: object

    # トークン情報のキャッシュ
    cache = {}

    @staticmethod
    def get(session, token_address: str):
        """
        株式トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: ShareToken
        """

        # IbetShare コントラクトへの接続
        TokenContract = Contract.get_contract("IbetShare", token_address)

        # キャッシュを利用する場合
        if config.TOKEN_CACHE:
            if token_address in ShareToken.cache:
                token_cache = ShareToken.cache[token_address]
                if token_cache.get("expiration_datetime") > datetime.utcnow():
                    # キャッシュ情報を取得
                    sharetoken = token_cache["token"]
                    # キャッシュ情報以外の情報を取得
                    sharetoken.total_supply = TokenContract.functions.totalSupply().call()
                    sharetoken.principal_value = TokenContract.functions.principalValue().call()
                    dividend_information = TokenContract.functions.dividendInformation().call()
                    sharetoken.dividend_information = {
                        'dividends': float(Decimal(str(dividend_information[0])) * Decimal("0.01")),
                        'dividend_record_date': dividend_information[1],
                        'dividend_payment_date': dividend_information[2],
                    }
                    sharetoken.transferable = TokenContract.functions.transferable().call()
                    sharetoken.is_offering = TokenContract.functions.isOffering().call()
                    sharetoken.status = TokenContract.functions.status().call()
                    sharetoken.transfer_approval_required = TokenContract.functions.transferApprovalRequired().call()
                    sharetoken.is_canceled = TokenContract.functions.isCanceled().call()
                    return sharetoken

        # キャッシュ未利用の場合
        # または、キャッシュに情報が存在しない場合
        # または、キャッシュの有効期限が切れている場合

        owner_address = TokenContract.functions.owner().call()
        name = TokenContract.functions.name().call()
        symbol = TokenContract.functions.symbol().call()
        total_supply = TokenContract.functions.totalSupply().call()
        issue_price = TokenContract.functions.issuePrice().call()
        principal_value = TokenContract.functions.principalValue().call()
        dividend_information = TokenContract.functions.dividendInformation().call()
        cancellation_date = TokenContract.functions.cancellationDate().call()
        memo = TokenContract.functions.memo().call()
        transferable = TokenContract.functions.transferable().call()
        is_offering = TokenContract.functions.isOffering().call()
        status = TokenContract.functions.status().call()
        transfer_approval_required = TokenContract.functions.transferApprovalRequired().call()
        is_canceled = TokenContract.functions.isCanceled().call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()
        tradable_exchange = TokenContract.functions.tradableExchange().call()
        personal_info_address = TokenContract.functions.personalInfoAddress().call()

        # 企業リストから、企業名とRSA鍵を取得する
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = session.query(Listing).filter(Listing.token_address == token_address).first()

        sharetoken = ShareToken()
        sharetoken.token_address = token_address
        sharetoken.token_template = "IbetShare"
        sharetoken.owner_address = owner_address
        sharetoken.company_name = company_name
        sharetoken.rsa_publickey = rsa_publickey
        sharetoken.name = name
        sharetoken.symbol = symbol
        sharetoken.total_supply = total_supply
        sharetoken.issue_price = issue_price
        sharetoken.principal_value = principal_value
        sharetoken.dividend_information = {
            'dividends': float(Decimal(str(dividend_information[0])) * Decimal("0.01")),
            'dividend_record_date': dividend_information[1],
            'dividend_payment_date': dividend_information[2],
        }
        sharetoken.cancellation_date = cancellation_date
        sharetoken.memo = memo
        sharetoken.transferable = transferable
        sharetoken.is_offering = is_offering
        sharetoken.status = status
        sharetoken.transfer_approval_required = transfer_approval_required
        sharetoken.is_canceled = is_canceled
        sharetoken.contact_information = contact_information
        sharetoken.privacy_policy = privacy_policy
        sharetoken.max_holding_quantity = listed_token.max_holding_quantity \
            if hasattr(listed_token, "max_holding_quantity") else 0
        sharetoken.max_sell_amount = listed_token.max_sell_amount \
            if hasattr(listed_token, "max_sell_amount") else 0
        sharetoken.tradable_exchange = tradable_exchange
        sharetoken.personal_info_address = personal_info_address

        if config.TOKEN_CACHE:
            ShareToken.cache[token_address] = {
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=config.TOKEN_CACHE_TTL),
                "token": sharetoken
            }

        return sharetoken


class MembershipToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    initial_offering_status: bool
    image_url: object

    # トークン情報のキャッシュ
    cache = {}

    @staticmethod
    def get(session, token_address: str):
        """
        会員権トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: MembershipToken
        """

        # Token-Contractへの接続
        TokenContract = Contract.get_contract('IbetMembership', token_address)

        # キャッシュを利用する場合
        if config.TOKEN_CACHE:
            if token_address in MembershipToken.cache:
                token_cache = MembershipToken.cache[token_address]
                if token_cache.get("expiration_datetime") > datetime.utcnow():
                    # キャッシュ情報を取得
                    membershiptoken = token_cache["token"]
                    # キャッシュ情報以外の情報を取得
                    transferable = TokenContract.functions.transferable().call()
                    status = TokenContract.functions.status().call()
                    initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
                    membershiptoken.transferable = transferable
                    membershiptoken.status = status
                    membershiptoken.initial_offering_status = initial_offering_status
                    return membershiptoken

        # キャッシュ未利用の場合
        # または、キャッシュに情報が存在しない場合
        # または、キャッシュの有効期限が切れている場合

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
        initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
        image_url_1 = TokenContract.functions.image_urls(0).call()
        image_url_2 = TokenContract.functions.image_urls(1).call()
        image_url_3 = TokenContract.functions.image_urls(2).call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()
        owner_address = TokenContract.functions.owner().call()
        tradable_exchange = TokenContract.functions.tradableExchange().call()

        # 企業リストから、企業名を取得する
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = session.query(Listing).filter(Listing.token_address == token_address).first()

        membershiptoken = MembershipToken()
        membershiptoken.token_address = token_address
        membershiptoken.token_template = 'IbetMembership'
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
            {'id': 1, 'url': image_url_1},
            {'id': 2, 'url': image_url_2},
            {'id': 3, 'url': image_url_3}
        ]
        membershiptoken.max_holding_quantity = listed_token.max_holding_quantity \
            if hasattr(listed_token, "max_holding_quantity") else 0
        membershiptoken.max_sell_amount = listed_token.max_sell_amount \
            if hasattr(listed_token, "max_sell_amount") else 0
        membershiptoken.contact_information = contact_information
        membershiptoken.privacy_policy = privacy_policy
        membershiptoken.tradable_exchange = tradable_exchange

        if config.TOKEN_CACHE:
            MembershipToken.cache[token_address] = {
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=config.TOKEN_CACHE_TTL),
                "token": membershiptoken
            }

        return membershiptoken


class CouponToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    initial_offering_status: bool
    image_url: object

    # トークン情報のキャッシュ
    cache = {}

    @staticmethod
    def get(session, token_address: str):
        """
        クーポントークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: CouponToken
        """

        # Token-Contractへの接続
        TokenContract = Contract.get_contract('IbetCoupon', token_address)

        # キャッシュを利用する場合
        if config.TOKEN_CACHE:
            if token_address in CouponToken.cache:
                token_cache = CouponToken.cache[token_address]
                if token_cache.get("expiration_datetime") > datetime.utcnow():
                    # キャッシュ情報を取得
                    coupontoken = token_cache["token"]
                    # キャッシュ情報以外の情報を取得
                    transferable = TokenContract.functions.transferable().call()
                    status = TokenContract.functions.status().call()
                    initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
                    coupontoken.transferable = transferable
                    coupontoken.status = status
                    coupontoken.initial_offering_status = initial_offering_status
                    return coupontoken

        # キャッシュ未利用の場合
        # または、キャッシュに情報が存在しない場合
        # または、キャッシュの有効期限が切れている場合

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
        initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
        image_url_1 = TokenContract.functions.image_urls(0).call()
        image_url_2 = TokenContract.functions.image_urls(1).call()
        image_url_3 = TokenContract.functions.image_urls(2).call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()
        owner_address = TokenContract.functions.owner().call()
        tradable_exchange = TokenContract.functions.tradableExchange().call()

        # 企業リストから、企業名を取得する
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = session.query(Listing).filter(Listing.token_address == token_address).first()

        coupontoken = CouponToken()
        coupontoken.token_address = token_address
        coupontoken.token_template = 'IbetCoupon'
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
            {'id': 1, 'url': image_url_1},
            {'id': 2, 'url': image_url_2},
            {'id': 3, 'url': image_url_3}
        ]
        coupontoken.max_holding_quantity = listed_token.max_holding_quantity \
            if hasattr(listed_token, "max_holding_quantity") else 0
        coupontoken.max_sell_amount = listed_token.max_sell_amount \
            if hasattr(listed_token, "max_sell_amount") else 0
        coupontoken.contact_information = contact_information
        coupontoken.privacy_policy = privacy_policy
        coupontoken.tradable_exchange = tradable_exchange

        if config.TOKEN_CACHE:
            CouponToken.cache[token_address] = {
                "expiration_datetime": datetime.utcnow() + timedelta(seconds=config.TOKEN_CACHE_TTL),
                "token": coupontoken
            }

        return coupontoken
