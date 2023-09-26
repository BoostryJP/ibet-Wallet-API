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
from decimal import Decimal
from typing import Annotated, Sequence, Type, Union

from eth_utils import to_checksum_address
from fastapi import APIRouter, Depends, Path, Request
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import sum as sum_
from web3 import Web3

from app import config, log
from app.contracts import Contract
from app.database import DBSession
from app.errors import (
    DataNotExistsError,
    InvalidParameterError,
    NotSupportedError,
    ServiceUnavailable,
)
from app.model.blockchain import (
    BondToken,
    CouponToken,
    MembershipToken,
    ShareToken,
    TokenClassTypes as BlockChainTokenModel,
)
from app.model.db import (
    IDXBondToken,
    IDXConsumeCoupon,
    IDXCouponToken,
    IDXLockedPosition,
    IDXMembershipToken,
    IDXPosition,
    IDXShareToken,
    IDXTokenInstance,
    IDXTokenListItem,
    IDXTokenModel,
    IDXTransfer,
    Listing,
)
from app.model.schema import (
    CouponPositionsResponse,
    CouponPositionWithAddress,
    CouponPositionWithDetail,
    GenericSecurityTokenPositionsResponse,
    GetPositionQuery,
    ListAllCouponConsumptionsResponse,
    ListAllPositionQuery,
    ListAllTokenPositionQuery,
    MembershipPositionsResponse,
    MembershipPositionWithAddress,
    MembershipPositionWithDetail,
    RetrieveShareTokenResponse,
    RetrieveStraightBondTokenResponse,
    SecurityTokenPositionWithAddress,
    SecurityTokenPositionWithDetail,
    TokenPositionsResponse,
)
from app.model.schema.base import GenericSuccessResponse, SuccessResponse, TokenType
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()


router = APIRouter(prefix="/Position", tags=["user_position"])


class BasePosition:
    # NOTE: Set Child class initializer.
    token_enabled: bool
    token_type: str
    token_model: BlockChainTokenModel
    idx_token_model: IDXTokenModel

    def __init__(
        self,
        token_enabled: bool,
        token_type: str,
        token_model: BlockChainTokenModel,
        idx_token_model: IDXTokenModel,
    ) -> None:
        self.token_enabled = token_enabled
        self.token_type = token_type
        self.token_model = token_model
        self.idx_token_model = idx_token_model

    def get_list(
        self,
        req: Request,
        request_query: ListAllPositionQuery,
        session: Session,
        account_address=None,
    ):
        # API Enabled Check
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.is_address(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")

        enable_index = request_query.enable_index

        if enable_index:
            # If enable_index flag is set true, get position data from DB.
            data = self.get_list_from_index(
                request_query=request_query,
                session=session,
                account_address=account_address,
            )
            return data

        # If enable_index flag is not set or set false, get position data from contract.
        data = self.get_list_from_contract(
            request_query=request_query,
            session=session,
            account_address=account_address,
        )
        return data

    def get_list_from_index(
        self,
        request_query: ListAllPositionQuery,
        session: Session,
        account_address: str,
    ):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details
        stmt = (
            select(
                Listing.token_address,
                IDXPosition,
                func.sum(IDXLockedPosition.value),
                self.idx_token_model,
            )
            .join(
                self.idx_token_model,
                Listing.token_address == self.idx_token_model.token_address,
            )
            .outerjoin(
                IDXPosition,
                and_(
                    Listing.token_address == IDXPosition.token_address,
                    IDXPosition.account_address == account_address,
                ),
            )
            .outerjoin(
                IDXLockedPosition,
                and_(
                    Listing.token_address == IDXLockedPosition.token_address,
                    IDXLockedPosition.account_address == account_address,
                ),
            )
            .where(
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.pending_transfer != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.exchange_commitment != 0,
                    IDXLockedPosition.value != 0,
                )
            )
            .group_by(
                Listing.id,
                IDXPosition.token_address,
                IDXPosition.account_address,
                self.idx_token_model.token_address,
                IDXLockedPosition.token_address,
            )
            .order_by(Listing.id)
        )

        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        count = total
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        _token_position_list: Sequence[
            tuple[str, IDXPosition, int | None, IDXTokenInstance]
        ] = (session.execute(stmt).tuples().all())

        position_list = []
        for item in _token_position_list:
            position = {
                "balance": item[1].balance if item[1] and item[1].balance else 0,
                "pending_transfer": item[1].pending_transfer
                if item[1] and item[1].pending_transfer
                else 0,
                "exchange_balance": item[1].exchange_balance
                if item[1] and item[1].exchange_balance
                else 0,
                "exchange_commitment": item[1].exchange_commitment
                if item[1] and item[1].exchange_commitment
                else 0,
                "locked": item[2] if item[2] else 0,
            }
            if include_token_details:
                position["token"] = self.token_model.from_model(item[3]).__dict__
            else:
                position["token_address"] = item[3].token_address
            position_list.append(position)
        return {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "positions": position_list,
        }

    def get_list_from_contract(
        self,
        request_query: ListAllPositionQuery,
        session: Session,
        account_address: str,
    ):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details
        # Get TokenList Contract
        _list_contract = Contract.get_contract(
            contract_name="TokenList", address=str(config.TOKEN_LIST_CONTRACT_ADDRESS)
        )

        # Get Listing Tokens
        _token_list: Sequence[Listing] = session.scalars(
            select(Listing).order_by(Listing.id)
        ).all()

        position_list = []
        limit_count = 0
        count = 0
        for _token in _token_list:
            token_info = Contract.call_function(
                contract=_list_contract,
                function_name="getTokenByAddress",
                args=(_token.token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
            )
            token_address = token_info[0]
            token_template = token_info[1]
            if token_template == self.token_type:
                # Get Position
                position = self._get_position(
                    account_address,
                    token_address,
                    session,
                    is_detail=include_token_details,
                )

                # Filter
                if position is None:
                    continue

                # Pagination
                if offset is not None and offset > count:
                    count += 1
                    continue
                if limit is not None and limit_count >= limit:
                    count += 1
                    continue

                position_list.append(position)
                count += 1
                limit_count += 1

        return {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": count,
            },
            "positions": position_list,
        }

    def get_one(
        self,
        req: Request,
        request_query: GetPositionQuery,
        session: Session,
        account_address: str,
        token_address: str,
    ):
        # API Enabled Check
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.is_address(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")
        try:
            token_address = to_checksum_address(token_address)
            if not Web3.is_address(token_address):
                raise InvalidParameterError(description="invalid token_address")
        except:
            raise InvalidParameterError(description="invalid token_address")

        enable_index = request_query.enable_index

        if enable_index:
            # If enable_index flag is set true, get position data from DB.
            data = self.get_one_from_index(
                session=session,
                account_address=account_address,
                token_address=token_address,
            )
            return data
        # If enable_index flag is not set or set false, get position data from contract.
        data = self.get_one_from_contract(
            session=session,
            account_address=account_address,
            token_address=token_address,
        )
        return data

    def get_one_from_index(
        self, session: Session, account_address: str, token_address: str
    ):
        stmt = (
            select(
                Listing.token_address,
                IDXPosition,
                func.sum(IDXLockedPosition.value),
                self.idx_token_model,
            )
            .join(
                self.idx_token_model,
                Listing.token_address == self.idx_token_model.token_address,
            )
            .outerjoin(
                IDXPosition,
                and_(
                    Listing.token_address == IDXPosition.token_address,
                    IDXPosition.account_address == account_address,
                ),
            )
            .outerjoin(
                IDXLockedPosition,
                and_(
                    Listing.token_address == IDXLockedPosition.token_address,
                    IDXLockedPosition.account_address == account_address,
                ),
            )
            .where(Listing.token_address == token_address)
            .where(
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.pending_transfer != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.exchange_commitment != 0,
                    IDXLockedPosition.value != 0,
                )
            )
            .group_by(
                Listing.id,
                IDXPosition.token_address,
                IDXPosition.account_address,
                self.idx_token_model.token_address,
                IDXLockedPosition.token_address,
            )
            .limit(1)
        )
        result: tuple[
            str, IDXPosition | None, int | None, IDXTokenInstance
        ] | None = session.execute(stmt).first()
        if result is None:
            raise DataNotExistsError(description="contract_address: %s" % token_address)
        _position = result[1]
        _locked = result[2]
        token = result[3]

        return {
            "balance": _position.balance if _position and _position.balance else 0,
            "pending_transfer": _position.pending_transfer
            if _position and _position.pending_transfer
            else 0,
            "exchange_balance": _position.exchange_balance
            if _position and _position.exchange_balance
            else 0,
            "exchange_commitment": _position.exchange_commitment
            if _position and _position.exchange_commitment
            else 0,
            "locked": _locked or 0,
            "token": self.token_model.from_model(token).__dict__,
        }

    def get_one_from_contract(
        self, session: Session, account_address: str, token_address: str
    ):
        # Get Listing Token
        _token = session.scalars(
            select(Listing).where(Listing.token_address == token_address).limit(1)
        ).first()
        if _token is None:
            raise DataNotExistsError(description="contract_address: %s" % token_address)

        # Get TokenList Contract
        _list_contract = Contract.get_contract(
            contract_name="TokenList", address=str(config.TOKEN_LIST_CONTRACT_ADDRESS)
        )
        token_info = Contract.call_function(
            contract=_list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS),
        )
        token_template = token_info[1]
        if token_template != self.token_type:
            raise DataNotExistsError(description="contract_address: %s" % token_address)

        # Get Position
        position = self._get_position(
            account_address, token_address, session, is_detail=True
        )
        if position is None:
            raise DataNotExistsError(description="contract_address: %s" % token_address)

        return position

    def _get_position(
        self,
        account_address: str,
        token_address: str,
        session: Session,
        is_detail=False,
    ):
        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0,
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0
            # If balance and commitment are non-zero,
            # get the token information from TokenContract.
            if balance == 0 and _exchange_balance == 0 and _exchange_commitment == 0:
                return None
            else:
                token = self.token_model.get(
                    session=session, token_address=token_address
                )
                position = {
                    "balance": balance,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except ServiceUnavailable as e:
            LOG.warning(e)
            return None
        except Exception as e:
            LOG.error(e)
            return None

    def _get_contract(self, token_address: str):
        # Get Token Contract
        _token_contract = Contract.get_contract(
            contract_name=self.token_type, address=token_address
        )

        # Get Exchange Contract
        exchange_address = Contract.call_function(
            contract=_token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=config.ZERO_ADDRESS,
        )
        _exchange_contract = None
        if exchange_address != config.ZERO_ADDRESS:
            _exchange_contract = Contract.get_contract(
                contract_name="IbetExchangeInterface", address=exchange_address
            )

        return _token_contract, _exchange_contract


class BasePositionShare(BasePosition):
    def __init__(self):
        super().__init__(
            config.SHARE_TOKEN_ENABLED, TokenType.IbetShare, ShareToken, IDXShareToken
        )

    def _get_position(
        self,
        account_address: str,
        token_address: str,
        session: Session,
        is_detail=False,
    ):
        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0,
            )
            pending_transfer = Contract.call_function(
                contract=_token_contract,
                function_name="pendingTransfer",
                args=(account_address,),
                default_returns=0,
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0

            # If balance, pending_transfer, and commitment are non-zero,
            # get the token information from TokenContract.
            if (
                balance == 0
                and pending_transfer == 0
                and _exchange_balance == 0
                and _exchange_commitment == 0
            ):
                return None
            else:
                token = ShareToken.get(session=session, token_address=token_address)
                position = {
                    "balance": balance,
                    "pending_transfer": pending_transfer,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                    "locked": None,
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except ServiceUnavailable as e:
            LOG.warning(e)
            return None
        except Exception as e:
            LOG.error(e)
            return None


class BasePositionStraightBond(BasePosition):
    def __init__(self):
        super().__init__(
            config.BOND_TOKEN_ENABLED,
            TokenType.IbetStraightBond,
            BondToken,
            IDXBondToken,
        )

    def _get_position(
        self,
        account_address: str,
        token_address: str,
        session: Session,
        is_detail=False,
    ):
        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0,
            )
            pending_transfer = Contract.call_function(
                contract=_token_contract,
                function_name="pendingTransfer",
                args=(account_address,),
                default_returns=0,
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0

            # If balance, pending_transfer, and commitment are non-zero,
            # get the token information from TokenContract.
            if (
                balance == 0
                and pending_transfer == 0
                and _exchange_balance == 0
                and _exchange_commitment == 0
            ):
                return None
            else:
                token = BondToken.get(session=session, token_address=token_address)
                position = {
                    "balance": balance,
                    "pending_transfer": pending_transfer,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                    "locked": None,
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except ServiceUnavailable as e:
            LOG.warning(e)
            return None
        except Exception as e:
            LOG.error(e)
            return None


class BasePositionMembership(BasePosition):
    def __init__(self):
        super().__init__(
            config.MEMBERSHIP_TOKEN_ENABLED,
            TokenType.IbetMembership,
            MembershipToken,
            IDXMembershipToken,
        )

    def get_list_from_index(
        self,
        request_query: ListAllPositionQuery,
        session: Session,
        account_address: str,
    ):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details
        stmt = (
            select(Listing.token_address, IDXPosition, self.idx_token_model)
            .join(
                self.idx_token_model,
                Listing.token_address == self.idx_token_model.token_address,
            )
            .join(IDXPosition, Listing.token_address == IDXPosition.token_address)
            .where(IDXPosition.account_address == account_address)
            .where(
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.exchange_commitment != 0,
                )
            )
            .order_by(Listing.id)
        )

        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        count = total
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        _token_position_list: Sequence[tuple[str, IDXPosition, IDXTokenInstance]] = (
            session.execute(stmt).tuples().all()
        )

        position_list = []
        for item in _token_position_list:
            position = {
                "balance": item[1].balance if item[1] and item[1].balance else 0,
                "exchange_balance": item[1].exchange_balance
                if item[1] and item[1].exchange_balance
                else 0,
                "exchange_commitment": item[1].exchange_commitment
                if item[1] and item[1].exchange_commitment
                else 0,
            }
            if include_token_details:
                position["token"] = self.token_model.from_model(item[2]).__dict__
            else:
                position["token_address"] = item[2].token_address
            position_list.append(position)
        return {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "positions": position_list,
        }


class BasePositionCoupon(BasePosition):
    def __init__(self):
        super().__init__(
            config.COUPON_TOKEN_ENABLED,
            TokenType.IbetCoupon,
            CouponToken,
            IDXCouponToken,
        )

    def get_list_from_index(
        self,
        request_query: ListAllPositionQuery,
        session: Session,
        account_address: str,
    ):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details

        # NOTE: Sub Query for sum of used amount
        sub_tx_used = (
            select(
                sum_(IDXConsumeCoupon.amount).label("used"),
                IDXConsumeCoupon.token_address,
                IDXConsumeCoupon.account_address,
            )
            .where(IDXConsumeCoupon.account_address == account_address)
            .group_by(IDXConsumeCoupon.token_address, IDXConsumeCoupon.account_address)
            .subquery("sub_tx_used")
        )
        stmt = (
            select(
                Listing.token_address,
                IDXPosition,
                self.idx_token_model,
                sub_tx_used.c.used,
            )
            .join(
                self.idx_token_model,
                Listing.token_address == self.idx_token_model.token_address,
            )
            .outerjoin(
                IDXPosition,
                and_(
                    Listing.token_address == IDXPosition.token_address,
                    IDXPosition.account_address == account_address,
                ),
            )
            .outerjoin(
                sub_tx_used,
                and_(
                    Listing.token_address == sub_tx_used.c.token_address,
                    sub_tx_used.c.account_address == account_address,
                ),
            )
            .where(
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.exchange_commitment != 0,
                    sub_tx_used.c.used != 0,
                    select(IDXTransfer)
                    .where(
                        and_(
                            IDXTransfer.token_address == Listing.token_address,
                            IDXTransfer.to_address == account_address,
                        )
                    )
                    .exists(),
                )
            )
            .order_by(Listing.id)
        )

        total = session.scalar(select(func.count()).select_from(stmt.subquery()))
        count = total
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)

        _token_position_list: Sequence[
            tuple[str, IDXPosition, IDXTokenInstance, Decimal | None]
        ] = (session.execute(stmt).tuples().all())

        position_list = []
        for item in _token_position_list:
            if item[1] is None:
                position = {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": int(item[3]) if item[3] else 0,
                }
            else:
                position = {
                    "balance": item[1].balance or 0,
                    "exchange_balance": item[1].exchange_balance or 0,
                    "exchange_commitment": item[1].exchange_commitment or 0,
                    "used": int(item[3]) if item[3] else 0,
                }
            if include_token_details:
                position["token"] = self.token_model.from_model(item[2]).__dict__
            else:
                position["token_address"] = item[2].token_address
            position_list.append(position)
        return {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "positions": position_list,
        }

    def _get_position(self, account_address, token_address, session, is_detail=False):
        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0,
            )
            used = Contract.call_function(
                contract=_token_contract,
                function_name="usedOf",
                args=(account_address,),
                default_returns=0,
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(
                        account_address,
                        token_address,
                    ),
                    default_returns=0,
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0

            # Retrieving token receipt history from IDXTransfer
            # NOTE: Index data has a lag from the most recent transfer state.
            received_history = session.scalars(
                select(IDXTransfer)
                .where(IDXTransfer.token_address == token_address)
                .where(IDXTransfer.to_address == account_address)
                .limit(1)
            ).first()
            # If balance, commitment, and used are non-zero, and exist received history,
            # get the token information from TokenContract.
            if (
                balance == 0
                and _exchange_balance == 0
                and _exchange_commitment == 0
                and used == 0
                and received_history is None
            ):
                return None
            else:
                token = CouponToken.get(session=session, token_address=token_address)
                position = {
                    "balance": balance,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                    "used": used,
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except ServiceUnavailable as e:
            LOG.warning(e)
            return None
        except Exception as e:
            LOG.error(e)
            return None


BasePositionType = Union[
    Type[BasePositionStraightBond]
    | Type[BasePositionShare]
    | Type[BasePositionMembership]
    | Type[BasePositionCoupon]
]


class GetPositionList:
    base_position: BasePositionType

    def __init__(self, base_position: BasePositionType):
        self.base_position = base_position

    def __call__(
        self,
        session: DBSession,
        req: Request,
        account_address: Annotated[str, Path(description="account address")],
        request_query: ListAllPositionQuery = Depends(),
    ):
        return self.base_position().get_list(
            req, request_query, session, account_address
        )


class GetPosition:
    base_position: BasePositionType

    def __init__(self, base_position: BasePositionType):
        self.base_position = base_position

    def __call__(
        self,
        session: DBSession,
        req: Request,
        account_address: Annotated[str, Path(description="account address")],
        token_address: Annotated[str, Path(description="token address")],
        request_query: GetPositionQuery = Depends(),
    ):
        return self.base_position().get_one(
            req, request_query, session, account_address, token_address
        )


# /Position/{account_address}/Share
@router.get(
    "/{account_address}/Share",
    summary="Share Token Position",
    operation_id="GetShareTokenPosition",
    response_model=GenericSuccessResponse[
        GenericSecurityTokenPositionsResponse[RetrieveShareTokenResponse]
    ],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def list_all_share_positions(
    positions: Union[
        list[SecurityTokenPositionWithDetail], list[SecurityTokenPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionShare))
):
    """
    List all share position
    """
    return json_response({**SuccessResponse.default(), "data": positions})


# /Position/{account_address}/StraightBond
@router.get(
    "/{account_address}/StraightBond",
    summary="StraightBond Token Position",
    operation_id="GetStraightBondTokenPosition",
    response_model=GenericSuccessResponse[
        GenericSecurityTokenPositionsResponse[RetrieveStraightBondTokenResponse]
    ],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def list_all_straight_bond_positions(
    positions: Union[
        list[SecurityTokenPositionWithDetail], list[SecurityTokenPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionStraightBond))
):
    """
    List all bond position
    """
    return json_response({**SuccessResponse.default(), "data": positions})


# /Position/{account_address}/Membership
@router.get(
    "/{account_address}/Membership",
    summary="Membership Token Position",
    operation_id="GetMembershipTokenPosition",
    response_model=GenericSuccessResponse[MembershipPositionsResponse],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def list_all_membership_positions(
    positions: Union[
        list[MembershipPositionWithDetail], list[MembershipPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionMembership))
):
    """
    List all membership position
    """
    return json_response({**SuccessResponse.default(), "data": positions})


# /Position/{account_address}/Coupon
@router.get(
    "/{account_address}/Coupon",
    summary="Coupon Token Position",
    operation_id="GetCouponTokenPosition",
    response_model=GenericSuccessResponse[CouponPositionsResponse],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def list_all_coupon_positions(
    positions: Union[
        list[CouponPositionWithDetail], list[CouponPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionCoupon))
):
    """
    List all coupon position
    """
    return json_response({**SuccessResponse.default(), "data": positions})


# /Position/{account_address}/Share/{token_address}
@router.get(
    "/{account_address}/Share/{token_address}",
    summary="Share Token Position By Token Address",
    operation_id="GetShareTokenPositionByAddress",
    response_model=GenericSuccessResponse[
        SecurityTokenPositionWithDetail[RetrieveShareTokenResponse]
    ],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def retrieve_share_position_by_token_address(
    position: SecurityTokenPositionWithDetail = Depends(GetPosition(BasePositionShare)),
):
    """
    Retrieve share position detail
    """
    return json_response({**SuccessResponse.default(), "data": position})


# /Position/{account_address}/StraightBond/{token_address}
@router.get(
    "/{account_address}/StraightBond/{token_address}",
    summary="StraightBond Token Position By Token Address",
    operation_id="GetStraightBondTokenPositionByAddress",
    response_model=GenericSuccessResponse[
        SecurityTokenPositionWithDetail[RetrieveStraightBondTokenResponse]
    ],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def retrieve_straight_bond_position_by_token_address(
    position: SecurityTokenPositionWithDetail = Depends(
        GetPosition(BasePositionStraightBond)
    ),
):
    """
    Retrieve bond position detail
    """
    return json_response({**SuccessResponse.default(), "data": position})


# /Position/{account_address}/Membership/{token_address}
@router.get(
    "/{account_address}/Membership/{token_address}",
    summary="Membership Token Position By Token Address",
    operation_id="GetMembershipTokenPositionByAddress",
    response_model=GenericSuccessResponse[MembershipPositionWithDetail],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def retrieve_membership_position_by_token_address(
    position: MembershipPositionWithDetail = Depends(
        GetPosition(BasePositionMembership)
    ),
):
    """
    Retrieve membership position detail
    """
    return json_response({**SuccessResponse.default(), "data": position})


# /Position/{account_address}/Coupon/{token_address}
@router.get(
    "/{account_address}/Coupon/{token_address}",
    summary="Coupon Token Position By Token Address",
    operation_id="GetCouponTokenPositionByAddress",
    response_model=GenericSuccessResponse[CouponPositionWithDetail],
    responses=get_routers_responses(
        DataNotExistsError, NotSupportedError, InvalidParameterError
    ),
)
def retrieve_coupon_position_by_token_address(
    position: CouponPositionWithDetail = Depends(GetPosition(BasePositionCoupon)),
):
    """
    Retrieve coupon position detail
    """
    return json_response({**SuccessResponse.default(), "data": position})


# /Position/{account_address}/Coupon/{token_address}/Consumptions
@router.get(
    "/{account_address}/Coupon/{token_address}/Consumptions",
    summary="List All Coupon Consumptions",
    operation_id="ListAllCouponConsumptions",
    response_model=GenericSuccessResponse[ListAllCouponConsumptionsResponse],
    responses=get_routers_responses(NotSupportedError),
)
def list_all_coupon_consumptions(
    session: DBSession,
    req: Request,
    account_address: Annotated[str, Path(description="account address")],
    token_address: Annotated[str, Path(description="token_address")],
):
    """
    List all coupon consumptions
    """
    if config.COUPON_TOKEN_ENABLED is False:
        raise NotSupportedError(method="GET", url=req.url.path)

    # 入力アドレスフォーマットチェック
    try:
        account_address = to_checksum_address(account_address)
        if not Web3.is_address(account_address):
            raise InvalidParameterError(description="invalid account_address")
    except:
        raise InvalidParameterError(description="invalid account_address")
    try:
        token_address = to_checksum_address(token_address)
        if not Web3.is_address(token_address):
            description = "invalid token_address"
            raise InvalidParameterError(description=description)
    except:
        description = "invalid token_address"
        raise InvalidParameterError(description=description)

    consumptions: Sequence[IDXConsumeCoupon] = session.scalars(
        select(IDXConsumeCoupon)
        .where(
            and_(
                IDXConsumeCoupon.token_address == token_address,
                IDXConsumeCoupon.account_address == account_address,
            )
        )
        .order_by(IDXConsumeCoupon.block_timestamp)
    ).all()

    res_data = []
    for consumption in consumptions:
        res_data.append(
            {
                "account_address": account_address,
                "block_timestamp": consumption.block_timestamp.strftime(
                    "%Y/%m/%d %H:%M:%S"
                ),
                "value": consumption.amount,
            }
        )

    return json_response({**SuccessResponse.default(), "data": res_data})


# /Position/{account_address}
@router.get(
    "/{account_address}",
    summary="Token Position",
    operation_id="GetTokenPosition",
    response_model=GenericSuccessResponse[TokenPositionsResponse],
    responses=get_routers_responses(InvalidParameterError),
)
def list_all_token_position(
    session: DBSession,
    account_address: Annotated[str, Path(description="account address")],
    request_query: ListAllTokenPositionQuery = Depends(),
):
    """
    List all positions
    """
    offset = request_query.offset
    limit = request_query.limit
    token_type_list = request_query.token_type_list

    include_bond_token = False
    include_share_token = False
    include_coupon_token = False
    include_membership_token = False

    if config.BOND_TOKEN_ENABLED and (
        not token_type_list or TokenType.IbetStraightBond in token_type_list
    ):
        include_bond_token = True
    if config.SHARE_TOKEN_ENABLED and (
        not token_type_list or TokenType.IbetShare in token_type_list
    ):
        include_share_token = True
    if config.COUPON_TOKEN_ENABLED and (
        not token_type_list or TokenType.IbetCoupon in token_type_list
    ):
        include_coupon_token = True
    if config.MEMBERSHIP_TOKEN_ENABLED and (
        not token_type_list or TokenType.IbetMembership in token_type_list
    ):
        include_membership_token = True

    query_target = [
        Listing.token_address,
        IDXTokenListItem.token_template,
        IDXPosition,
        func.sum(IDXLockedPosition.value),
        func.sum(IDXConsumeCoupon.amount),
        IDXBondToken if include_bond_token else None,
        IDXShareToken if include_share_token else None,
        IDXCouponToken if include_coupon_token else None,
        IDXMembershipToken if include_membership_token else None,
    ]
    group_by_columns = [
        Listing.id,
        IDXTokenListItem.token_address,
        IDXPosition.token_address,
        IDXPosition.account_address,
        IDXLockedPosition.token_address,
        IDXConsumeCoupon.token_address,
    ]
    token_type_filter = []

    if include_bond_token:
        group_by_columns.append(IDXBondToken.token_address)
        token_type_filter.append(
            IDXTokenListItem.token_template == TokenType.IbetStraightBond.value
        )
    if include_share_token:
        group_by_columns.append(IDXShareToken.token_address)
        token_type_filter.append(
            IDXTokenListItem.token_template == TokenType.IbetShare.value
        )
    if include_coupon_token:
        group_by_columns.append(IDXCouponToken.token_address)
        token_type_filter.append(
            IDXTokenListItem.token_template == TokenType.IbetCoupon.value
        )
    if include_membership_token:
        group_by_columns.append(IDXMembershipToken.token_address)
        token_type_filter.append(
            IDXTokenListItem.token_template == TokenType.IbetMembership.value
        )

    stmt = (
        select(*query_target)
        .join(
            IDXTokenListItem,
            and_(
                IDXTokenListItem.token_address == Listing.token_address,
                or_(*token_type_filter),
            ),
        )
        .outerjoin(
            IDXPosition,
            and_(
                IDXPosition.token_address == Listing.token_address,
                IDXPosition.account_address == account_address,
            ),
        )
        .outerjoin(
            IDXLockedPosition,
            and_(
                Listing.token_address == IDXLockedPosition.token_address,
                IDXLockedPosition.account_address == account_address,
            ),
        )
        .outerjoin(
            IDXConsumeCoupon,
            and_(
                Listing.token_address == IDXConsumeCoupon.token_address,
                IDXConsumeCoupon.account_address == account_address,
            ),
        )
    )

    if not token_type_list or TokenType.IbetStraightBond in token_type_list:
        stmt = stmt.outerjoin(
            IDXBondToken,
            Listing.token_address == IDXBondToken.token_address,
        )

    if not token_type_list or TokenType.IbetShare in token_type_list:
        stmt = stmt.outerjoin(
            IDXShareToken,
            Listing.token_address == IDXShareToken.token_address,
        )

    if not token_type_list or TokenType.IbetCoupon in token_type_list:
        stmt = stmt.outerjoin(
            IDXCouponToken,
            Listing.token_address == IDXCouponToken.token_address,
        )

    if not token_type_list or TokenType.IbetMembership in token_type_list:
        stmt = stmt.outerjoin(
            IDXMembershipToken,
            Listing.token_address == IDXMembershipToken.token_address,
        )

    stmt = (
        stmt.where(
            or_(
                IDXPosition.balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0,
                IDXConsumeCoupon.amount != 0,
            )
        )
        .group_by(*group_by_columns)
        .order_by(Listing.id)
    )

    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    count = total

    if limit is not None:
        stmt = stmt.limit(limit)
    if offset is not None:
        stmt = stmt.offset(offset)

    _token_position_list = session.execute(stmt).all()

    position_list = []
    for item in _token_position_list:
        if item[1] == TokenType.IbetStraightBond.value:
            position_list.append(
                {
                    **IDXPosition.bond(item[2]),
                    "locked": item[3] if item[3] else 0,
                    "token": BondToken.from_model(item[5]).__dict__,
                }
            )
        elif item[1] == TokenType.IbetShare.value:
            position_list.append(
                {
                    **IDXPosition.share(item[2]),
                    "locked": item[3] if item[3] else 0,
                    "token": ShareToken.from_model(item[6]).__dict__,
                }
            )
        elif item[1] == TokenType.IbetCoupon.value:
            position_list.append(
                {
                    **IDXPosition.coupon(item[2]),
                    "used": int(item[4]) if item[4] else 0,
                    "token": CouponToken.from_model(item[7]).__dict__,
                }
            )
        elif item[1] == TokenType.IbetMembership.value:
            position_list.append(
                {
                    **IDXPosition.membership(item[2]),
                    "token": MembershipToken.from_model(item[8]).__dict__,
                }
            )

    data = {
        "result_set": {
            "count": count,
            "offset": offset,
            "limit": limit,
            "total": total,
        },
        "positions": position_list,
    }
    return json_response({**SuccessResponse.default(), "data": data})
