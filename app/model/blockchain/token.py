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
from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from eth_utils import to_checksum_address
import functools
from typing import Union, Type, Optional, Callable
from sqlalchemy.orm import Session

from app import log
from app.config import (
    ZERO_ADDRESS,
    TOKEN_CACHE,
    TOKEN_CACHE_TTL,
    TOKEN_SHORT_TERM_CACHE_TTL,

)
from app.contracts import Contract
from app.model.db import (
    Listing,
    IDXBondToken as BondTokenModel,
    IDXShareToken as ShareTokenModel,
    IDXMembershipToken as MembershipTokenModel,
    IDXCouponToken as CouponTokenModel,
)
from app.model.db.idx_token import IDXTokenModel, IDXTokenInstance
from app.utils.company_list import CompanyList

LOG = log.get_logger()

TokenClassTypes = Union[
    Type['BondToken'],
    Type['ShareToken'],
    Type['MembershipToken'],
    Type['CouponToken']]

TokenInstanceTypes = Union[
    'BondToken',
    'ShareToken',
    'MembershipToken',
    'CouponToken'
]


def token_db_cache(TargetModel: IDXTokenModel):
    """
    Cache decorator for Token Details
    @param TargetModel: DB model for cache
    """

    def decorator(func: Callable[[TokenClassTypes, Session, str], Optional[TokenInstanceTypes]]):
        """
        @param func: Function for decoration
        """
        @functools.wraps(func)
        def wrapper(cls: TokenClassTypes, session: Session, token_address: str) -> Optional[TokenInstanceTypes]:
            """
            @param cls: Class of return instance
            @param session: ORM session
            @param token_address: Address of token which will be cached
            @return Token detail instance
            """
            if not TOKEN_CACHE:
                # If token cache is not enabled, use raw data from chain
                return func(cls, session, token_address)

            # Get data from cache
            cached_token: Optional[IDXTokenInstance] = session.query(TargetModel). \
                filter(TargetModel.token_address == token_address). \
                first()
            if cached_token and cached_token.created + timedelta(seconds=TOKEN_CACHE_TTL) >= datetime.utcnow():
                # If cached data exists and doesn't expire, use cached data
                cached_data = cls.from_model(cached_token)
                if cached_token.short_term_cache_created + timedelta(seconds=TOKEN_SHORT_TERM_CACHE_TTL) < datetime.utcnow():
                    # If short term cache expires, fetch raw data from chain
                    cached_data.fetch_expiry_short()
                    session.merge(cached_data.to_model())
                return cached_data

            # Get data from chain
            return func(cls, session, token_address)

        return wrapper

    return decorator


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

    @staticmethod
    def from_model(token: TokenBase):
        raise NotImplementedError("Subclasses should implement this")

    def to_model(self):
        raise NotImplementedError("Subclasses should implement this")


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

    @staticmethod
    def from_model(token_model: BondTokenModel) -> BondToken:
        token_obj = BondToken()
        for key, value in token_model.json().items():
            if key != "interest_payment_date":
                setattr(token_obj, key, value)

        interest_payment_date_list = token_model.interest_payment_date
        for i, d in enumerate(interest_payment_date_list):
            setattr(token_obj, f"interest_payment_date{str(i+1)}", d)

        return token_obj

    def to_model(self) -> BondTokenModel:
        token_model = BondTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)

        interest_payment_date_list = []
        for i in range(1, 13):
            if getattr(self, f"interest_payment_date{str(i)}", None):
                interest_payment_date_list.append(getattr(self, f"interest_payment_date{str(i)}"))
        token_model.interest_payment_date = interest_payment_date_list
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    def fetch_expiry_short(self) -> None:
        """
        債権トークン リアルタイム属性情報取得

        :return: None
        """
        token_contract = Contract.get_contract('IbetStraightBond', self.token_address)

        # Fetch
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        status = Contract.call_function(token_contract, "status", (), True)

        transferable = Contract.call_function(token_contract, "transferable", (), False)
        is_offering = Contract.call_function(token_contract, "isOffering", (), False)
        transfer_approval_required = Contract.call_function(token_contract, "transferApprovalRequired", (), False)
        is_redeemed = Contract.call_function(token_contract, "isRedeemed", (), False)

        # Update
        self.owner_address = owner_address
        self.company_name = company_name
        self.rsa_publickey = rsa_publickey
        self.total_supply = total_supply
        self.status = status
        self.transferable = transferable
        self.is_offering = is_offering
        self.transfer_approval_required = transfer_approval_required
        self.is_redeemed = is_redeemed

    @staticmethod
    def fetch(session: Session, token_address: str) -> BondToken:
        """
        債券トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: BondToken
        """

        # IbetStraightBond コントラクトへの接続
        token_contract = Contract.get_contract('IbetStraightBond', token_address)

        # Contractから情報を取得する
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        name = Contract.call_function(token_contract, "name", (), "")
        symbol = Contract.call_function(token_contract, "symbol", (), "")
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        face_value = Contract.call_function(token_contract, "faceValue", (), 0)
        interest_rate = Contract.call_function(token_contract, "interestRate", (), 0)

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
            interest_payment_date_string = Contract.call_function(token_contract, "interestPaymentDate", (), "")
            if interest_payment_date_string != "":
                interest_payment_date = json.loads(
                    interest_payment_date_string.replace("'", '"').replace('True', 'true').replace('False', 'false')
                )
            else:
                interest_payment_date = {}
            if 'interestPaymentDate1' in interest_payment_date:
                interest_payment_date1 = interest_payment_date.get('interestPaymentDate1', '')
            if 'interestPaymentDate2' in interest_payment_date:
                interest_payment_date2 = interest_payment_date.get('interestPaymentDate2', '')
            if 'interestPaymentDate3' in interest_payment_date:
                interest_payment_date3 = interest_payment_date.get('interestPaymentDate3', '')
            if 'interestPaymentDate4' in interest_payment_date:
                interest_payment_date4 = interest_payment_date.get('interestPaymentDate4', '')
            if 'interestPaymentDate5' in interest_payment_date:
                interest_payment_date5 = interest_payment_date.get('interestPaymentDate5', '')
            if 'interestPaymentDate6' in interest_payment_date:
                interest_payment_date6 = interest_payment_date.get('interestPaymentDate6', '')
            if 'interestPaymentDate7' in interest_payment_date:
                interest_payment_date7 = interest_payment_date.get('interestPaymentDate7', '')
            if 'interestPaymentDate8' in interest_payment_date:
                interest_payment_date8 = interest_payment_date.get('interestPaymentDate8', '')
            if 'interestPaymentDate9' in interest_payment_date:
                interest_payment_date9 = interest_payment_date.get('interestPaymentDate9', '')
            if 'interestPaymentDate10' in interest_payment_date:
                interest_payment_date10 = interest_payment_date.get('interestPaymentDate10', '')
            if 'interestPaymentDate11' in interest_payment_date:
                interest_payment_date11 = interest_payment_date.get('interestPaymentDate11', '')
            if 'interestPaymentDate12' in interest_payment_date:
                interest_payment_date12 = interest_payment_date.get('interestPaymentDate12', '')
        except Exception:
            LOG.warning("Failed to load interestPaymentDate")

        redemption_date = Contract.call_function(token_contract, "redemptionDate", (), "")
        redemption_value = Contract.call_function(token_contract, "redemptionValue", (), 0)

        return_date = Contract.call_function(token_contract, "returnDate", (), "")
        return_amount = Contract.call_function(token_contract, "returnAmount", (), "")
        purpose = Contract.call_function(token_contract, "purpose", (), "")
        transferable = Contract.call_function(token_contract, "transferable", (), False)
        is_offering = Contract.call_function(token_contract, "isOffering", (), False)
        contact_information = Contract.call_function(token_contract, "contactInformation", (), "")
        privacy_policy = Contract.call_function(token_contract, "privacyPolicy", (), "")
        tradable_exchange = Contract.call_function(token_contract, "tradableExchange", (), ZERO_ADDRESS)
        status = Contract.call_function(token_contract, "status", (), True)
        memo = Contract.call_function(token_contract, "memo", (), "")
        personal_info_address = Contract.call_function(token_contract, "personalInfoAddress", (), ZERO_ADDRESS)
        transfer_approval_required = Contract.call_function(token_contract, "transferApprovalRequired", (), False)
        is_redeemed = Contract.call_function(token_contract, "isRedeemed", (), False)

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

        return bondtoken

    @classmethod
    @token_db_cache(BondTokenModel)
    def get(cls, session: Session, token_address: str) -> BondToken:
        return cls.fetch(session, token_address)


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

    @staticmethod
    def from_model(token_model: ShareTokenModel) -> ShareToken:
        token_obj = ShareToken()
        for key, value in token_model.json().items():
            setattr(token_obj, key, value)
        return token_obj

    def to_model(self) -> 'ShareTokenModel':
        token_model = ShareTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    def fetch_expiry_short(self) -> None:
        """
        株式トークン リアルタイム属性情報取得

        :return: ShareToken
        """
        token_contract = Contract.get_contract("IbetShare", self.token_address)

        # Fetch
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        status = Contract.call_function(token_contract, "status", (), True)

        transferable = Contract.call_function(token_contract, "transferable", (), False)
        is_offering = Contract.call_function(token_contract, "isOffering", (), False)
        transfer_approval_required = Contract.call_function(token_contract, "transferApprovalRequired", (), False)
        principal_value = Contract.call_function(token_contract, "principalValue", (), 0)
        is_canceled = Contract.call_function(token_contract, "isCanceled", (), False)
        dividend_information = Contract.call_function(
            token_contract, "dividendInformation", (), (0, "", "")
        )

        # Update
        self.owner_address = owner_address
        self.company_name = company_name
        self.rsa_publickey = rsa_publickey
        self.total_supply = total_supply
        self.status = status
        self.transferable = transferable
        self.is_offering = is_offering
        self.transfer_approval_required = transfer_approval_required
        self.principal_value = principal_value
        self.is_canceled = is_canceled
        self.dividend_information = {
            'dividends': float(Decimal(str(dividend_information[0])) * Decimal("0.01")),
            'dividend_record_date': dividend_information[1],
            'dividend_payment_date': dividend_information[2],
        }

    @staticmethod
    def fetch(session: Session, token_address: str) -> ShareToken:
        """
        株式トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: ShareToken
        """

        # IbetShare コントラクトへの接続
        token_contract = Contract.get_contract("IbetShare", token_address)
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        name = Contract.call_function(token_contract, "name", (), "")
        symbol = Contract.call_function(token_contract, "symbol", (), "")
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        issue_price = Contract.call_function(token_contract, "issuePrice", (), 0)
        principal_value = Contract.call_function(token_contract, "principalValue", (), 0)
        dividend_information = Contract.call_function(
            token_contract, "dividendInformation", (), (0, "", "")
        )
        cancellation_date = Contract.call_function(token_contract, "cancellationDate", (), "")
        memo = Contract.call_function(token_contract, "memo", (), "")
        status = Contract.call_function(token_contract, "status", (), True)
        transferable = Contract.call_function(token_contract, "transferable", (), False)
        transfer_approval_required = Contract.call_function(token_contract, "transferApprovalRequired", (), False)
        is_offering = Contract.call_function(token_contract, "isOffering", (), False)
        contact_information = Contract.call_function(token_contract, "contactInformation", (), "")
        privacy_policy = Contract.call_function(token_contract, "privacyPolicy", (), "")
        tradable_exchange = Contract.call_function(token_contract, "tradableExchange", (), ZERO_ADDRESS)
        personal_info_address = Contract.call_function(token_contract, "personalInfoAddress", (), ZERO_ADDRESS)
        is_canceled = Contract.call_function(token_contract, "isCanceled", (), False)

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

        return sharetoken

    @classmethod
    @token_db_cache(ShareTokenModel)
    def get(cls, session: Session, token_address: str) -> ShareToken:
        return cls.fetch(session, token_address)


class MembershipToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: bool
    initial_offering_status: bool
    image_url: object

    @staticmethod
    def from_model(token_model: MembershipTokenModel) -> MembershipToken:
        token_obj = MembershipToken()
        for key, value in token_model.json().items():
            setattr(token_obj, key, value)
        return token_obj

    def to_model(self) -> 'MembershipTokenModel':
        token_model = MembershipTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    def fetch_expiry_short(self) -> None:
        """
        会員権トークン リアルタイム属性情報取得

        :return: None
        """
        token_contract = Contract.get_contract('IbetMembership', self.token_address)

        # Fetch
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        status = Contract.call_function(token_contract, "status", (), True)

        transferable = Contract.call_function(token_contract, "transferable", (), False)
        initial_offering_status = Contract.call_function(
            token_contract, "initialOfferingStatus", (), False
        )

        # Update
        self.owner_address = owner_address
        self.company_name = company_name
        self.rsa_publickey = rsa_publickey
        self.total_supply = total_supply
        self.status = status
        self.transferable = transferable
        self.initial_offering_status = initial_offering_status

    @staticmethod
    def fetch(session: Session, token_address: str) -> MembershipToken:
        """
        会員権トークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: MembershipToken
        """

        # Token-Contractへの接続
        token_contract = Contract.get_contract('IbetMembership', token_address)

        # Token-Contractから情報を取得する
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        name = Contract.call_function(token_contract, "name", (), "")
        symbol = Contract.call_function(token_contract, "symbol", (), "")
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        details = Contract.call_function(token_contract, "details", (), "")
        return_details = Contract.call_function(token_contract, "returnDetails", (), "")
        expiration_date = Contract.call_function(token_contract, "expirationDate", (), "")
        memo = Contract.call_function(token_contract, "memo", (), "")
        transferable = Contract.call_function(token_contract, "transferable", (), False)
        status = Contract.call_function(token_contract, "status", (), True)
        initial_offering_status = Contract.call_function(
            token_contract, "initialOfferingStatus", (), False
        )
        image_url_1 = Contract.call_function(token_contract, "image_urls", (0,), "")
        image_url_2 = Contract.call_function(token_contract, "image_urls", (1,), "")
        image_url_3 = Contract.call_function(token_contract, "image_urls", (2,), "")
        contact_information = Contract.call_function(token_contract, "contactInformation", (), "")
        privacy_policy = Contract.call_function(token_contract, "privacyPolicy", (), "")
        tradable_exchange = Contract.call_function(token_contract, "tradableExchange", (), ZERO_ADDRESS)

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

        return membershiptoken

    @classmethod
    @token_db_cache(MembershipTokenModel)
    def get(cls, session: Session, token_address: str) -> MembershipToken:
        return cls.fetch(session, token_address)


class CouponToken(TokenBase):
    details: str
    return_details: str
    expiration_date: str
    memo: str
    transferable: str
    initial_offering_status: bool
    image_url: object

    @staticmethod
    def from_model(token_model: CouponTokenModel) -> CouponToken:
        token_obj = CouponToken()
        for key, value in token_model.json().items():
            setattr(token_obj, key, value)
        return token_obj

    def to_model(self) -> 'CouponTokenModel':
        token_model = CouponTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    def fetch_expiry_short(self) -> None:
        """
        クーポントークン リアルタイム属性情報取得

        :return: None
        """
        token_contract = Contract.get_contract('IbetCoupon', self.token_address)

        # Fetch
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        company = CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        status = Contract.call_function(token_contract, "status", (), True)

        transferable = Contract.call_function(token_contract, "transferable", (), False)
        initial_offering_status = Contract.call_function(
            token_contract, "initialOfferingStatus", (), False
        )

        # Update
        self.owner_address = owner_address
        self.company_name = company_name
        self.rsa_publickey = rsa_publickey
        self.total_supply = total_supply
        self.status = status
        self.transferable = transferable
        self.initial_offering_status = initial_offering_status

    @staticmethod
    def fetch(session: Session, token_address: str) -> CouponToken:
        """
        クーポントークン属性情報取得

        :param session: DB session
        :param token_address: トークンアドレス
        :return: CouponToken
        """

        # Token-Contractへの接続
        token_contract = Contract.get_contract('IbetCoupon', token_address)

        # Token-Contractから情報を取得する
        owner_address = Contract.call_function(token_contract, "owner", (), ZERO_ADDRESS)
        name = Contract.call_function(token_contract, "name", (), "")
        symbol = Contract.call_function(token_contract, "symbol", (), "")
        total_supply = Contract.call_function(token_contract, "totalSupply", (), 0)
        details = Contract.call_function(token_contract, "details", (), "")
        return_details = Contract.call_function(token_contract, "returnDetails", (), "")
        expiration_date = Contract.call_function(token_contract, "expirationDate", (), "")
        memo = Contract.call_function(token_contract, "memo", (), "")
        transferable = Contract.call_function(token_contract, "transferable", (), False)
        status = Contract.call_function(token_contract, "status", (), True)
        initial_offering_status = Contract.call_function(
            token_contract, "initialOfferingStatus", (), False
        )
        image_url_1 = Contract.call_function(token_contract, "image_urls", (0,), "")
        image_url_2 = Contract.call_function(token_contract, "image_urls", (1,), "")
        image_url_3 = Contract.call_function(token_contract, "image_urls", (2,), "")
        contact_information = Contract.call_function(token_contract, "contactInformation", (), "")
        privacy_policy = Contract.call_function(token_contract, "privacyPolicy", (), "")
        tradable_exchange = Contract.call_function(token_contract, "tradableExchange", (), ZERO_ADDRESS)

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

        return coupontoken

    @classmethod
    @token_db_cache(CouponTokenModel)
    def get(cls, session: Session, token_address: str) -> CouponToken:
        return cls.fetch(session, token_address)
