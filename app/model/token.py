"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

import json
from decimal import Decimal

import requests
from eth_utils import to_checksum_address

from app import config
from app import log
from app.contracts import Contract
from app.model import Listing

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
    image_url: object
    contact_information: str
    privacy_policy: str


class BondToken(TokenBase):
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
    isRedeemed: bool
    transferable: bool
    certification: str
    initial_offering_status: bool
    max_holding_quantity: int
    max_sell_amount: int

    @staticmethod
    def get(session, token_address: str):
        """
        債券トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: BondToken
        """

        # 企業リストの情報を取得する
        company_list = []
        if config.APP_ENV == 'local' or config.COMPANY_LIST_LOCAL_MODE is True:
            company_list = json.load(open('data/company_list.json', 'r'))
        else:
            try:
                company_list = requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
            except Exception as err:
                LOG.err("Failed to get company list: ", err)
                pass

        # IbetStraightBond コントラクトへの接続
        TokenContract = Contract.get_contract('IbetStraightBond', token_address)

        # Contractから情報を取得する
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
        except Exception as err:
            LOG.warning("Failed to load interestPaymentDate: ", err)
            pass

        redemption_date = TokenContract.functions.redemptionDate().call()
        redemption_value = TokenContract.functions.redemptionValue().call()
        return_date = TokenContract.functions.returnDate().call()
        return_amount = TokenContract.functions.returnAmount().call()
        purpose = TokenContract.functions.purpose().call()
        isRedeemed = TokenContract.functions.isRedeemed().call()
        transferable = TokenContract.functions.transferable().call()
        initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
        image_url_1 = TokenContract.functions.getImageURL(0).call()
        image_url_2 = TokenContract.functions.getImageURL(1).call()
        image_url_3 = TokenContract.functions.getImageURL(2).call()
        owner_address = TokenContract.functions.owner().call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()

        # 企業リストから、企業名を取得する
        company_name = ""
        rsa_publickey = ""
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']

        # 取扱トークンリストからその他属性情報を取得
        listed_token = session.query(Listing).filter(Listing.token_address == token_address).first()

        # 第三者認定（Sign）のイベント情報を検索する
        # NOTE:現状項目未使用であるため空のリストを返す
        certification = []
        bondtoken = BondToken()
        bondtoken.token_address = token_address
        bondtoken.token_template = 'IbetStraightBond'
        bondtoken.owner_address = owner_address
        bondtoken.company_name = company_name
        bondtoken.rsa_publickey = rsa_publickey
        bondtoken.name = name
        bondtoken.symbol = symbol
        bondtoken.total_supply = total_supply
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
        bondtoken.isRedeemed = isRedeemed
        bondtoken.transferable = transferable
        bondtoken.image_url = [
            {'id': 1, 'url': image_url_1},
            {'id': 2, 'url': image_url_2},
            {'id': 3, 'url': image_url_3}
        ]
        bondtoken.certification = certification
        bondtoken.initial_offering_status = initial_offering_status
        bondtoken.max_holding_quantity = listed_token.max_holding_quantity \
            if hasattr(listed_token, "max_holding_quantity") else 0
        bondtoken.max_sell_amount = listed_token.max_sell_amount \
            if hasattr(listed_token, "max_sell_amount") else 0
        bondtoken.contact_information = contact_information
        bondtoken.privacy_policy = privacy_policy

        return bondtoken


class ShareToken(TokenBase):
    issue_price: int
    dividend_information: object
    cancellation_date: str
    reference_urls: object
    memo: str
    transferable: bool
    offering_status: bool
    status: bool
    reference_urls: object
    max_holding_quantity: int
    max_sell_amount: int

    @staticmethod
    def get(session, token_address: str):
        """
        株式トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: ShareToken
        """

        # 企業リストの情報を取得する
        company_list = []
        if config.APP_ENV == 'local' or config.COMPANY_LIST_LOCAL_MODE is True:
            company_list = json.load(open('data/company_list.json', 'r'))
        else:
            try:
                company_list = requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
            except Exception as err:
                LOG.err("Failed to get company list: ", err)
                pass

        # IbetShare コントラクトへの接続
        TokenContract = Contract.get_contract("IbetShare", token_address)

        owner_address = TokenContract.functions.owner().call()
        name = TokenContract.functions.name().call()
        symbol = TokenContract.functions.symbol().call()
        total_supply = TokenContract.functions.totalSupply().call()
        issue_price = TokenContract.functions.issuePrice().call()
        dividend_information = TokenContract.functions.dividendInformation().call()
        cancellation_date = TokenContract.functions.cancellationDate().call()
        reference_url_1 = TokenContract.functions.referenceUrls(0).call()
        reference_url_2 = TokenContract.functions.referenceUrls(1).call()
        reference_url_3 = TokenContract.functions.referenceUrls(2).call()
        memo = TokenContract.functions.memo().call()
        transferable = TokenContract.functions.transferable().call()
        offering_status = TokenContract.functions.offeringStatus().call()
        status = TokenContract.functions.status().call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()

        # 企業リストから、企業名とRSA鍵を取得する
        company_name = ''
        rsa_publickey = ''
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']

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
        sharetoken.dividend_information = {
            'dividends': float(Decimal(str(dividend_information[0])) * Decimal("0.01")),
            'dividend_record_date': dividend_information[1],
            'dividend_payment_date': dividend_information[2],
        }
        sharetoken.cancellation_date = cancellation_date
        sharetoken.reference_urls = [
            {'id': 1, 'url': reference_url_1},
            {'id': 2, 'url': reference_url_2},
            {'id': 3, 'url': reference_url_3},
        ]
        sharetoken.image_url = []
        sharetoken.memo = memo
        sharetoken.transferable = transferable
        sharetoken.offering_status = offering_status
        sharetoken.status = status
        sharetoken.contact_information = contact_information
        sharetoken.privacy_policy = privacy_policy
        sharetoken.max_holding_quantity = listed_token.max_holding_quantity \
            if hasattr(listed_token, "max_holding_quantity") else 0
        sharetoken.max_sell_amount = listed_token.max_sell_amount \
            if hasattr(listed_token, "max_sell_amount") else 0

        return sharetoken


class MembershipToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    status: str
    initial_offering_status: str
    max_holding_quantity: int
    max_sell_amount: int

    @staticmethod
    def get(session, token_address: str):
        """
        会員権トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: MembershipToken
        """

        # 企業リストの情報を取得する
        company_list = []
        if config.APP_ENV == 'local' or config.COMPANY_LIST_LOCAL_MODE is True:
            company_list = json.load(open('data/company_list.json', 'r'))
        else:
            try:
                company_list = requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
            except Exception as err:
                LOG.err("Failed to get company list: ", err)
                pass

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
        initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
        image_url_1 = TokenContract.functions.image_urls(0).call()
        image_url_2 = TokenContract.functions.image_urls(1).call()
        image_url_3 = TokenContract.functions.image_urls(2).call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()

        owner_address = TokenContract.functions.owner().call()

        # 企業リストから、企業名を取得する
        company_name = ""
        rsa_publickey = ""
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']

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

        return membershiptoken


class CouponToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    status: str
    initial_offering_status: str
    max_holding_quantity: int
    max_sell_amount: int

    @staticmethod
    def get(session, token_address: str):
        # 企業リストの情報を取得する
        company_list = []
        if config.APP_ENV == 'local' or config.COMPANY_LIST_LOCAL_MODE is True:
            company_list = json.load(open('data/company_list.json', 'r'))
        else:
            try:
                company_list = requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
            except Exception as err:
                LOG.err("Failed to get company list: ", err)
                pass

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
        initial_offering_status = TokenContract.functions.initialOfferingStatus().call()
        image_url_1 = TokenContract.functions.image_urls(0).call()
        image_url_2 = TokenContract.functions.image_urls(1).call()
        image_url_3 = TokenContract.functions.image_urls(2).call()
        contact_information = TokenContract.functions.contactInformation().call()
        privacy_policy = TokenContract.functions.privacyPolicy().call()

        owner_address = TokenContract.functions.owner().call()

        # 企業リストから、企業名を取得する
        company_name = ""
        rsa_publickey = ""
        for company in company_list:
            if to_checksum_address(company['address']) == owner_address:
                company_name = company['corporate_name']
                rsa_publickey = company['rsa_publickey']

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

        return coupontoken
