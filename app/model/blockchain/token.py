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

import functools
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Awaitable, Callable, Optional, Type, Union

from eth_utils import to_checksum_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import log
from app.config import (
    DEFAULT_CURRENCY,
    TOKEN_CACHE,
    TOKEN_CACHE_TTL,
    TOKEN_SHORT_TERM_CACHE_TTL,
    ZERO_ADDRESS,
)
from app.contracts import AsyncContract
from app.errors import ServiceUnavailable
from app.model.db import (
    IDXBondToken as BondTokenModel,
    IDXCouponToken as CouponTokenModel,
    IDXMembershipToken as MembershipTokenModel,
    IDXShareToken as ShareTokenModel,
    Listing,
)
from app.model.db.idx_token import IDXTokenInstance, IDXTokenModel
from app.model.schema.base import TokenType
from app.utils.asyncio_utils import SemaphoreTaskGroup
from app.utils.company_list import CompanyList

LOG = log.get_logger()

TokenClassTypes = Union[
    Type["BondToken"], Type["ShareToken"], Type["MembershipToken"], Type["CouponToken"]
]

TokenInstanceTypes = Union["BondToken", "ShareToken", "MembershipToken", "CouponToken"]


def token_db_cache(TargetModel: IDXTokenModel):
    """
    Cache decorator for Token Details
    @param TargetModel: DB model for cache
    """

    def decorator(
        func: Callable[
            [TokenClassTypes, AsyncSession, str],
            Awaitable[Optional[TokenInstanceTypes]],
        ]
    ):
        """
        @param func: Function for decoration
        """

        @functools.wraps(func)
        async def wrapper(
            cls: TokenClassTypes, async_session: AsyncSession, token_address: str
        ) -> Optional[TokenInstanceTypes]:
            """
            @param cls: Class of return instance
            @param async_session: ORM async session
            @param token_address: Address of token which will be cached
            @return Token detail instance
            """
            if not TOKEN_CACHE:
                # If token cache is not enabled, use raw data from chain
                return await func(cls, async_session, token_address)

            # Get data from cache
            cached_token: Optional[IDXTokenInstance] = (
                await async_session.scalars(
                    select(TargetModel)
                    .where(TargetModel.token_address == token_address)
                    .limit(1)
                )
            ).first()
            if (
                cached_token
                and cached_token.created + timedelta(seconds=TOKEN_CACHE_TTL)
                >= datetime.utcnow()
            ):
                # If cached data exists and doesn't expire, use cached data
                cached_data = cls.from_model(cached_token)
                if (
                    cached_token.short_term_cache_created
                    + timedelta(seconds=TOKEN_SHORT_TERM_CACHE_TTL)
                    < datetime.utcnow()
                ):
                    # If short term cache expires, fetch raw data from chain
                    await cached_data.fetch_expiry_short()
                    await async_session.merge(cached_data.to_model())
                return cached_data

            # Get data from chain
            return await func(cls, async_session, token_address)

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
    face_value_currency: str
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
    interest_payment_currency: str
    redemption_date: str
    redemption_value: int
    redemption_value_currency: str
    base_fx_rate: float
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
                interest_payment_date_list.append(
                    getattr(self, f"interest_payment_date{str(i)}")
                )
        token_model.interest_payment_date = interest_payment_date_list
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    async def fetch_expiry_short(self) -> None:
        """
        債権トークン リアルタイム属性情報取得

        :return: None
        """
        token_contract = AsyncContract.get_contract(
            TokenType.IbetStraightBond, self.token_address
        )
        # Fetch
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(token_contract, "isOffering", (), False),
                AsyncContract.call_function(
                    token_contract, "transferApprovalRequired", (), False
                ),
                AsyncContract.call_function(token_contract, "isRedeemed", (), False),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                max_concurrency=3,
            )
            (
                owner_address,
                total_supply,
                status,
                transferable,
                is_offering,
                transfer_approval_required,
                is_redeemed,
                memo,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

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
        self.memo = memo

    @staticmethod
    async def fetch(async_session: AsyncSession, token_address: str) -> BondToken:
        """
        債券トークン属性情報取得

        :param async_session: DB Async session
        :param token_address: トークンアドレス
        :return: BondToken
        """

        # IbetStraightBond コントラクトへの接続
        token_contract = AsyncContract.get_contract(
            TokenType.IbetStraightBond, token_address
        )

        # Token-Contractから情報を取得する
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "name", (), ""),
                AsyncContract.call_function(token_contract, "symbol", (), ""),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "faceValue", (), 0),
                AsyncContract.call_function(
                    token_contract, "faceValueCurrency", (), DEFAULT_CURRENCY
                ),
                AsyncContract.call_function(token_contract, "interestRate", (), 0),
                AsyncContract.call_function(
                    token_contract, "interestPaymentDate", (), ""
                ),
                AsyncContract.call_function(token_contract, "redemptionDate", (), ""),
                AsyncContract.call_function(
                    token_contract, "interestPaymentCurrency", (), ""
                ),
                AsyncContract.call_function(token_contract, "redemptionValue", (), 0),
                AsyncContract.call_function(
                    token_contract, "redemptionValueCurrency", (), ""
                ),
                AsyncContract.call_function(token_contract, "baseFXRate", (), ""),
                AsyncContract.call_function(token_contract, "returnDate", (), ""),
                AsyncContract.call_function(token_contract, "returnAmount", (), ""),
                AsyncContract.call_function(token_contract, "purpose", (), ""),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(token_contract, "isOffering", (), False),
                AsyncContract.call_function(
                    token_contract, "contactInformation", (), ""
                ),
                AsyncContract.call_function(token_contract, "privacyPolicy", (), ""),
                AsyncContract.call_function(
                    token_contract, "tradableExchange", (), ZERO_ADDRESS
                ),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                AsyncContract.call_function(
                    token_contract, "personalInfoAddress", (), ZERO_ADDRESS
                ),
                AsyncContract.call_function(
                    token_contract, "transferApprovalRequired", (), False
                ),
                AsyncContract.call_function(token_contract, "isRedeemed", (), False),
                max_concurrency=3,
            )
            (
                owner_address,
                name,
                symbol,
                total_supply,
                face_value,
                face_value_currency,
                interest_rate,
                interest_payment_date_string,
                redemption_date,
                interest_payment_currency,
                redemption_value,
                redemption_value_currency,
                _raw_base_fx_rate,
                return_date,
                return_amount,
                purpose,
                transferable,
                is_offering,
                contact_information,
                privacy_policy,
                tradable_exchange,
                status,
                memo,
                personal_info_address,
                transfer_approval_required,
                is_redeemed,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        interest_payment_date1 = ""
        interest_payment_date2 = ""
        interest_payment_date3 = ""
        interest_payment_date4 = ""
        interest_payment_date5 = ""
        interest_payment_date6 = ""
        interest_payment_date7 = ""
        interest_payment_date8 = ""
        interest_payment_date9 = ""
        interest_payment_date10 = ""
        interest_payment_date11 = ""
        interest_payment_date12 = ""
        try:
            if interest_payment_date_string != "":
                interest_payment_date = json.loads(
                    interest_payment_date_string.replace("'", '"')
                    .replace("True", "true")
                    .replace("False", "false")
                )
            else:
                interest_payment_date = {}
            if "interestPaymentDate1" in interest_payment_date:
                interest_payment_date1 = interest_payment_date.get(
                    "interestPaymentDate1", ""
                )
            if "interestPaymentDate2" in interest_payment_date:
                interest_payment_date2 = interest_payment_date.get(
                    "interestPaymentDate2", ""
                )
            if "interestPaymentDate3" in interest_payment_date:
                interest_payment_date3 = interest_payment_date.get(
                    "interestPaymentDate3", ""
                )
            if "interestPaymentDate4" in interest_payment_date:
                interest_payment_date4 = interest_payment_date.get(
                    "interestPaymentDate4", ""
                )
            if "interestPaymentDate5" in interest_payment_date:
                interest_payment_date5 = interest_payment_date.get(
                    "interestPaymentDate5", ""
                )
            if "interestPaymentDate6" in interest_payment_date:
                interest_payment_date6 = interest_payment_date.get(
                    "interestPaymentDate6", ""
                )
            if "interestPaymentDate7" in interest_payment_date:
                interest_payment_date7 = interest_payment_date.get(
                    "interestPaymentDate7", ""
                )
            if "interestPaymentDate8" in interest_payment_date:
                interest_payment_date8 = interest_payment_date.get(
                    "interestPaymentDate8", ""
                )
            if "interestPaymentDate9" in interest_payment_date:
                interest_payment_date9 = interest_payment_date.get(
                    "interestPaymentDate9", ""
                )
            if "interestPaymentDate10" in interest_payment_date:
                interest_payment_date10 = interest_payment_date.get(
                    "interestPaymentDate10", ""
                )
            if "interestPaymentDate11" in interest_payment_date:
                interest_payment_date11 = interest_payment_date.get(
                    "interestPaymentDate11", ""
                )
            if "interestPaymentDate12" in interest_payment_date:
                interest_payment_date12 = interest_payment_date.get(
                    "interestPaymentDate12", ""
                )
        except Exception:
            LOG.warning("Failed to load interestPaymentDate")

        try:
            if _raw_base_fx_rate is not None and _raw_base_fx_rate != "":
                base_fx_rate = float(_raw_base_fx_rate)
            else:
                base_fx_rate = 0.0
        except ValueError:
            base_fx_rate = 0.0

        # 企業リストから、企業名を取得する
        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = (
            await async_session.scalars(
                select(Listing).where(Listing.token_address == token_address).limit(1)
            )
        ).first()

        bondtoken = BondToken()
        bondtoken.token_address = token_address
        bondtoken.token_template = TokenType.IbetStraightBond
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
        bondtoken.max_holding_quantity = (
            listed_token.max_holding_quantity
            if hasattr(listed_token, "max_holding_quantity")
            else 0
        )
        bondtoken.max_sell_amount = (
            listed_token.max_sell_amount
            if hasattr(listed_token, "max_sell_amount")
            else 0
        )
        bondtoken.personal_info_address = personal_info_address
        bondtoken.transferable = transferable
        bondtoken.is_offering = is_offering
        bondtoken.transfer_approval_required = transfer_approval_required
        bondtoken.face_value = face_value
        bondtoken.face_value_currency = face_value_currency
        bondtoken.interest_rate = float(Decimal(str(interest_rate)) * Decimal("0.0001"))
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
        bondtoken.interest_payment_currency = interest_payment_currency
        bondtoken.redemption_date = redemption_date
        bondtoken.redemption_value = redemption_value
        bondtoken.redemption_value_currency = redemption_value_currency
        bondtoken.base_fx_rate = base_fx_rate
        bondtoken.return_date = return_date
        bondtoken.return_amount = return_amount
        bondtoken.purpose = purpose
        bondtoken.memo = memo
        bondtoken.is_redeemed = is_redeemed

        return bondtoken

    @classmethod
    @token_db_cache(BondTokenModel)
    async def get(cls, async_session: AsyncSession, token_address: str) -> BondToken:
        return await cls.fetch(async_session, token_address)


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

    def to_model(self) -> "ShareTokenModel":
        token_model = ShareTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    async def fetch_expiry_short(self) -> None:
        """
        株式トークン リアルタイム属性情報取得

        :return: ShareToken
        """
        token_contract = AsyncContract.get_contract(
            TokenType.IbetShare, self.token_address
        )

        # Fetch
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(token_contract, "isOffering", (), False),
                AsyncContract.call_function(
                    token_contract, "transferApprovalRequired", (), False
                ),
                AsyncContract.call_function(token_contract, "principalValue", (), 0),
                AsyncContract.call_function(token_contract, "isCanceled", (), False),
                AsyncContract.call_function(
                    token_contract, "dividendInformation", (), (0, "", "")
                ),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                max_concurrency=3,
            )
            (
                owner_address,
                total_supply,
                status,
                transferable,
                is_offering,
                transfer_approval_required,
                principal_value,
                is_canceled,
                dividend_information,
                memo,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

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
            "dividends": float(
                Decimal(str(dividend_information[0])) * Decimal("0.0000000000001")
            ),
            "dividend_record_date": dividend_information[1],
            "dividend_payment_date": dividend_information[2],
        }
        self.memo = memo

    @staticmethod
    async def fetch(async_session: AsyncSession, token_address: str) -> ShareToken:
        """
        株式トークン属性情報取得

        :param async_session: DB Async session
        :param token_address: トークンアドレス
        :return: ShareToken
        """

        # IbetShare コントラクトへの接続
        token_contract = AsyncContract.get_contract(TokenType.IbetShare, token_address)

        # Token-Contractから情報を取得する
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "name", (), ""),
                AsyncContract.call_function(token_contract, "symbol", (), ""),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "issuePrice", (), 0),
                AsyncContract.call_function(token_contract, "principalValue", (), 0),
                AsyncContract.call_function(
                    token_contract, "dividendInformation", (), (0, "", "")
                ),
                AsyncContract.call_function(token_contract, "cancellationDate", (), ""),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(
                    token_contract, "transferApprovalRequired", (), False
                ),
                AsyncContract.call_function(token_contract, "isOffering", (), False),
                AsyncContract.call_function(
                    token_contract, "contactInformation", (), ""
                ),
                AsyncContract.call_function(token_contract, "privacyPolicy", (), ""),
                AsyncContract.call_function(
                    token_contract, "tradableExchange", (), ZERO_ADDRESS
                ),
                AsyncContract.call_function(
                    token_contract, "personalInfoAddress", (), ZERO_ADDRESS
                ),
                AsyncContract.call_function(token_contract, "isCanceled", (), False),
                max_concurrency=3,
            )
            (
                owner_address,
                name,
                symbol,
                total_supply,
                issue_price,
                principal_value,
                dividend_information,
                cancellation_date,
                memo,
                status,
                transferable,
                transfer_approval_required,
                is_offering,
                contact_information,
                privacy_policy,
                tradable_exchange,
                personal_info_address,
                is_canceled,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        # 企業リストから、企業名とRSA鍵を取得する
        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = (
            await async_session.scalars(
                select(Listing).where(Listing.token_address == token_address).limit(1)
            )
        ).first()

        sharetoken = ShareToken()
        sharetoken.token_address = token_address
        sharetoken.token_template = TokenType.IbetShare
        sharetoken.owner_address = owner_address
        sharetoken.company_name = company_name
        sharetoken.rsa_publickey = rsa_publickey
        sharetoken.name = name
        sharetoken.symbol = symbol
        sharetoken.total_supply = total_supply
        sharetoken.issue_price = issue_price
        sharetoken.principal_value = principal_value
        sharetoken.dividend_information = {
            "dividends": float(
                Decimal(str(dividend_information[0])) * Decimal("0.0000000000001")
            ),
            "dividend_record_date": dividend_information[1],
            "dividend_payment_date": dividend_information[2],
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
        sharetoken.max_holding_quantity = (
            listed_token.max_holding_quantity
            if hasattr(listed_token, "max_holding_quantity")
            else 0
        )
        sharetoken.max_sell_amount = (
            listed_token.max_sell_amount
            if hasattr(listed_token, "max_sell_amount")
            else 0
        )
        sharetoken.tradable_exchange = tradable_exchange
        sharetoken.personal_info_address = personal_info_address

        return sharetoken

    @classmethod
    @token_db_cache(ShareTokenModel)
    async def get(cls, async_session: AsyncSession, token_address: str) -> ShareToken:
        return await cls.fetch(async_session, token_address)


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

    def to_model(self) -> "MembershipTokenModel":
        token_model = MembershipTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    async def fetch_expiry_short(self) -> None:
        """
        会員権トークン リアルタイム属性情報取得

        :return: None
        """
        token_contract = AsyncContract.get_contract(
            TokenType.IbetMembership, self.token_address
        )

        # Fetch
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(
                    token_contract, "initialOfferingStatus", (), False
                ),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                max_concurrency=3,
            )
            (
                owner_address,
                total_supply,
                status,
                transferable,
                initial_offering_status,
                memo,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # Update
        self.owner_address = owner_address
        self.company_name = company_name
        self.rsa_publickey = rsa_publickey
        self.total_supply = total_supply
        self.status = status
        self.transferable = transferable
        self.initial_offering_status = initial_offering_status
        self.memo = memo

    @staticmethod
    async def fetch(async_session: AsyncSession, token_address: str) -> MembershipToken:
        """
        会員権トークン属性情報取得

        :param async_session: DB Async session
        :param token_address: トークンアドレス
        :return: MembershipToken
        """

        # Token-Contractへの接続
        token_contract = AsyncContract.get_contract(
            TokenType.IbetMembership, token_address
        )

        # Token-Contractから情報を取得する
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "name", (), ""),
                AsyncContract.call_function(token_contract, "symbol", (), ""),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "details", (), ""),
                AsyncContract.call_function(token_contract, "returnDetails", (), ""),
                AsyncContract.call_function(token_contract, "expirationDate", (), ""),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(
                    token_contract, "initialOfferingStatus", (), False
                ),
                AsyncContract.call_function(token_contract, "image_urls", (0,), ""),
                AsyncContract.call_function(token_contract, "image_urls", (1,), ""),
                AsyncContract.call_function(token_contract, "image_urls", (2,), ""),
                AsyncContract.call_function(
                    token_contract, "contactInformation", (), ""
                ),
                AsyncContract.call_function(token_contract, "privacyPolicy", (), ""),
                AsyncContract.call_function(
                    token_contract, "tradableExchange", (), ZERO_ADDRESS
                ),
                max_concurrency=3,
            )
            (
                owner_address,
                name,
                symbol,
                total_supply,
                details,
                return_details,
                expiration_date,
                memo,
                transferable,
                status,
                initial_offering_status,
                image_url_1,
                image_url_2,
                image_url_3,
                contact_information,
                privacy_policy,
                tradable_exchange,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        # 企業リストから、企業名を取得する
        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = (
            await async_session.scalars(
                select(Listing).where(Listing.token_address == token_address).limit(1)
            )
        ).first()

        membershiptoken = MembershipToken()
        membershiptoken.token_address = token_address
        membershiptoken.token_template = TokenType.IbetMembership
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
            {"id": 1, "url": image_url_1},
            {"id": 2, "url": image_url_2},
            {"id": 3, "url": image_url_3},
        ]
        membershiptoken.max_holding_quantity = (
            listed_token.max_holding_quantity
            if hasattr(listed_token, "max_holding_quantity")
            else 0
        )
        membershiptoken.max_sell_amount = (
            listed_token.max_sell_amount
            if hasattr(listed_token, "max_sell_amount")
            else 0
        )
        membershiptoken.contact_information = contact_information
        membershiptoken.privacy_policy = privacy_policy
        membershiptoken.tradable_exchange = tradable_exchange

        return membershiptoken

    @classmethod
    @token_db_cache(MembershipTokenModel)
    async def get(
        cls, async_session: AsyncSession, token_address: str
    ) -> MembershipToken:
        return await cls.fetch(async_session, token_address)


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

    def to_model(self) -> "CouponTokenModel":
        token_model = CouponTokenModel()
        for key, value in self.__dict__.items():
            if hasattr(token_model, key):
                setattr(token_model, key, value)
        token_model.short_term_cache_created = datetime.utcnow()
        return token_model

    async def fetch_expiry_short(self) -> None:
        """
        クーポントークン リアルタイム属性情報取得

        :return: None
        """
        token_contract = AsyncContract.get_contract(
            TokenType.IbetCoupon, self.token_address
        )

        # Fetch
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(
                    token_contract, "initialOfferingStatus", (), False
                ),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                max_concurrency=3,
            )
            (
                owner_address,
                total_supply,
                status,
                transferable,
                initial_offering_status,
                memo,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # Update
        self.owner_address = owner_address
        self.company_name = company_name
        self.rsa_publickey = rsa_publickey
        self.total_supply = total_supply
        self.status = status
        self.transferable = transferable
        self.initial_offering_status = initial_offering_status
        self.memo = memo

    @staticmethod
    async def fetch(async_session: AsyncSession, token_address: str) -> CouponToken:
        """
        クーポントークン属性情報取得

        :param async_session: DB Async session
        :param token_address: トークンアドレス
        :return: CouponToken
        """

        # Token-Contractへの接続
        token_contract = AsyncContract.get_contract(TokenType.IbetCoupon, token_address)

        # Token-Contractから情報を取得する
        try:
            tasks = await SemaphoreTaskGroup.run(
                AsyncContract.call_function(token_contract, "owner", (), ZERO_ADDRESS),
                AsyncContract.call_function(token_contract, "name", (), ""),
                AsyncContract.call_function(token_contract, "symbol", (), ""),
                AsyncContract.call_function(token_contract, "totalSupply", (), 0),
                AsyncContract.call_function(token_contract, "details", (), ""),
                AsyncContract.call_function(token_contract, "returnDetails", (), ""),
                AsyncContract.call_function(token_contract, "expirationDate", (), ""),
                AsyncContract.call_function(token_contract, "memo", (), ""),
                AsyncContract.call_function(token_contract, "transferable", (), False),
                AsyncContract.call_function(token_contract, "status", (), True),
                AsyncContract.call_function(
                    token_contract, "initialOfferingStatus", (), False
                ),
                AsyncContract.call_function(token_contract, "image_urls", (0,), ""),
                AsyncContract.call_function(token_contract, "image_urls", (1,), ""),
                AsyncContract.call_function(token_contract, "image_urls", (2,), ""),
                AsyncContract.call_function(
                    token_contract, "contactInformation", (), ""
                ),
                AsyncContract.call_function(token_contract, "privacyPolicy", (), ""),
                AsyncContract.call_function(
                    token_contract, "tradableExchange", (), ZERO_ADDRESS
                ),
                max_concurrency=3,
            )
            (
                owner_address,
                name,
                symbol,
                total_supply,
                details,
                return_details,
                expiration_date,
                memo,
                transferable,
                status,
                initial_offering_status,
                image_url_1,
                image_url_2,
                image_url_3,
                contact_information,
                privacy_policy,
                tradable_exchange,
            ) = [task.result() for task in tasks]
        except ExceptionGroup:
            raise ServiceUnavailable from None

        # 企業リストから、企業名を取得する
        company = await CompanyList.get_find(to_checksum_address(owner_address))
        company_name = company.corporate_name
        rsa_publickey = company.rsa_publickey

        # 取扱トークンリストからその他属性情報を取得
        listed_token = (
            await async_session.scalars(
                select(Listing).where(Listing.token_address == token_address).limit(1)
            )
        ).first()

        coupontoken = CouponToken()
        coupontoken.token_address = token_address
        coupontoken.token_template = TokenType.IbetCoupon
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
            {"id": 1, "url": image_url_1},
            {"id": 2, "url": image_url_2},
            {"id": 3, "url": image_url_3},
        ]
        coupontoken.max_holding_quantity = (
            listed_token.max_holding_quantity
            if hasattr(listed_token, "max_holding_quantity")
            else 0
        )
        coupontoken.max_sell_amount = (
            listed_token.max_sell_amount
            if hasattr(listed_token, "max_sell_amount")
            else 0
        )
        coupontoken.contact_information = contact_information
        coupontoken.privacy_policy = privacy_policy
        coupontoken.tradable_exchange = tradable_exchange

        return coupontoken

    @classmethod
    @token_db_cache(CouponTokenModel)
    async def get(cls, async_session: AsyncSession, token_address: str) -> CouponToken:
        return await cls.fetch(async_session, token_address)
