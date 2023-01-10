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
from datetime import (
    timedelta,
    timezone
)
from decimal import Decimal
from eth_utils import to_checksum_address
from fastapi import (
    APIRouter,
    Depends,
    Request,
    Path
)
from sqlalchemy import (
    or_,
    and_,
    func,
    desc,
    literal,
    String,
    null,
    column,
    cast
)
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import sum as sum_
from typing import (
    Union,
    Type
)
from web3 import Web3

from app import config
from app import log
from app.contracts import Contract
from app.database import db_session
from app.errors import (
    InvalidParameterError,
    DataNotExistsError,
    NotSupportedError
)
from app.model.db import (
    Listing,
    IDXTransfer,
    IDXPosition,
    IDXTokenModel,
    IDXConsumeCoupon,
    IDXTokenInstance,
    IDXShareToken,
    IDXBondToken,
    IDXCouponToken,
    IDXMembershipToken,
    IDXLockedPosition,
    IDXLock,
    IDXUnlock
)
from app.model.blockchain import (
    ShareToken,
    BondToken,
    MembershipToken,
    CouponToken,
    TokenClassTypes as BlockChainTokenModel
)
from app.model.schema import (
    ListAllPositionQuery,
    GenericSuccessResponse,
    SuccessResponse,
    SecurityTokenPositionWithDetail,
    GenericSecurityTokenPositionsResponse,
    SecurityTokenPositionWithAddress,
    MembershipPositionsResponse,
    MembershipPositionWithDetail,
    MembershipPositionWithAddress,
    CouponPositionsResponse,
    CouponPositionWithDetail,
    CouponPositionWithAddress,
    RetrieveStraightBondTokenResponse,
    RetrieveShareTokenResponse,
    GetPositionQuery,
    ListAllLockedPositionQuery,
    ListLockedResponse,
    ListAllLockEventQuery,
    LockEventCategory,
    LockEventSortItem,
    LockEventsResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response

LOG = log.get_logger()

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")

router = APIRouter(
    prefix="/Position",
    tags=["user_position"]
)



class ListAllLock:
    token_enabled: bool

    def __init__(self, token_enabled: bool):
        self.token_enabled = token_enabled

    def __call__(
        self,
        req: Request,
        request_query: ListAllLockedPositionQuery = Depends(),
        account_address: str = Path(),
        session: Session = Depends(db_session)
    ):
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.isAddress(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")

        token_address_list = request_query.token_address_list
        lock_address = request_query.lock_address
        limit = request_query.limit
        offset = request_query.offset

        sort_item = request_query.sort_item
        sort_order = request_query.sort_order  # default: asc

        query = session.query(IDXLockedPosition)
        if len(token_address_list) > 0:
            query = query.filter(IDXLockedPosition.token_address.in_(token_address_list))
        query = query.filter(IDXLockedPosition.account_address == account_address)

        total = query.count()

        if lock_address is not None:
            query = query.filter(IDXLockedPosition.lock_address == lock_address)

        count = query.count()

        sort_attr = getattr(IDXLockedPosition, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))

        # NOTE: Set secondary sort for consistent results
        if sort_item != "token_address":
            query = query.order_by(IDXLockedPosition.token_address)
        else:
            query = query.order_by(IDXLockedPosition.created)

        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _locked_list: list[IDXLockedPosition] = query.all()
        locked_list = []

        for _locked in _locked_list:
            locked_list.append(_locked.json())

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "locked_list": locked_list
        }

        return data


class ListAllLockEvent:
    token_enabled: bool

    def __init__(self, token_enabled: bool):
        self.token_enabled = token_enabled

    def __call__(
        self,
        req: Request,
        request_query: ListAllLockEventQuery = Depends(),
        account_address: str = Path(),
        session: Session = Depends(db_session)
    ):
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.isAddress(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")

        category = request_query.category

        query_lock = session.query(
            literal(value=LockEventCategory.Lock.value, type_=String).label("history_category"),
            IDXLock.transaction_hash.label("transaction_hash"),
            IDXLock.token_address.label("token_address"),
            IDXLock.lock_address.label("lock_address"),
            IDXLock.account_address.label("account_address"),
            null().label("recipient_address"),
            IDXLock.value.label("value"),
            IDXLock.data.label("data"),
            IDXLock.block_timestamp.label("block_timestamp")
        )
        query_unlock = session.query(
            literal(value=LockEventCategory.Unlock.value, type_=String).label("history_category"),
            IDXUnlock.transaction_hash.label("transaction_hash"),
            IDXUnlock.token_address.label("token_address"),
            IDXUnlock.lock_address.label("lock_address"),
            IDXUnlock.account_address.label("account_address"),
            IDXUnlock.recipient_address.label("recipient_address"),
            IDXUnlock.value.label("value"),
            IDXUnlock.data.label("data"),
            IDXUnlock.block_timestamp.label("block_timestamp")
        )

        total = query_lock.count() + query_unlock.count()

        match category:
            case LockEventCategory.Lock:
                query = query_lock
            case LockEventCategory.Unlock:
                query = query_unlock
            case _:
                query = query_lock.union_all(query_unlock)

        query = query.filter(column("account_address") == account_address)

        if request_query.token_address is not None:
            query = query.filter(column("token_address") == request_query.token_address)
        if request_query.lock_address is not None:
            query = query.filter(column("lock_address") == request_query.lock_address)
        if request_query.recipient_address is not None:
            query = query.filter(column("recipient_address") == request_query.recipient_address)
        if request_query.data is not None:
            query = query.filter(cast(column("data"), String).like("%" + request_query.data + "%"))
        count = query.count()

        # Sort
        sort_attr = column(request_query.sort_item)
        if request_query.sort_order == 0:  # ASC
            query = query.order_by(sort_attr.is_(None), sort_attr)
        else:  # DESC
            query = query.order_by(sort_attr.is_(None), desc(sort_attr))
        if request_query.sort_item != LockEventSortItem.block_timestamp:
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(desc(column(LockEventSortItem.block_timestamp)))

        # Pagination
        if request_query.offset is not None:
            query = query.offset(request_query.offset)
        if request_query.limit is not None:
            query = query.limit(request_query.limit)
        lock_events = query.all()

        resp_data = []
        for lock_event in lock_events:
            resp_data.append({
                "category": lock_event[0],
                "transaction_hash": lock_event[1],
                "token_address": lock_event[2],
                "lock_address": lock_event[3],
                "account_address": lock_event[4],
                "recipient_address": lock_event[5],
                "value": lock_event[6],
                "data": lock_event[7],
                "block_timestamp": lock_event[8].replace(tzinfo=UTC).astimezone(JST)
            })

        data = {
            "result_set": {
                "count": count,
                "offset": request_query.offset,
                "limit": request_query.limit,
                "total": total
            },
            "events": resp_data
        }
        return data

# ------------------------------
# Get Lock(Share)
# ------------------------------
@router.get(
    "/{account_address}/Share/Lock",
    summary="Share Token Locked Position",
    operation_id="GetShareTokenLockedPosition",
    response_model=GenericSuccessResponse[ListLockedResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def list_all_share_locks(
    data: dict = Depends(ListAllLock(config.SHARE_TOKEN_ENABLED))
):
    return json_response({
        **SuccessResponse.default(),
        "data": data
    })


# ------------------------------
# Get Lock Event(Share)
# ------------------------------
@router.get(
    "/{account_address}/Share/Lock/Event",
    summary="Share Token Lock Events",
    operation_id="GetShareTokenLockEvent",
    response_model=GenericSuccessResponse[LockEventsResponse],
    responses=get_routers_responses()
)
def list_all_share_lock_events(
    data: dict = Depends(ListAllLockEvent(config.SHARE_TOKEN_ENABLED))
):
    return json_response({
        **SuccessResponse.default(),
        "data": data
    })

# ------------------------------
# Get Lock(StraightBond)
# ------------------------------
@router.get(
    "/{account_address}/StraightBond/Lock",
    summary="StraightBond Token Locked Position",
    operation_id="GetStraightBondTokenLockedPosition",
    response_model=GenericSuccessResponse[ListLockedResponse],
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError)
)
def list_all_straight_bond_locks(
    data: dict = Depends(ListAllLock(config.BOND_TOKEN_ENABLED))
):
    return json_response({
        **SuccessResponse.default(),
        "data": data
    })


# ------------------------------
# Get Lock Event(StraightBond)
# ------------------------------
@router.get(
    "/{account_address}/StraightBond/Lock/Event",
    summary="StraightBond Token Lock Events",
    operation_id="GetStraightBondTokenLockEvent",
    response_model=GenericSuccessResponse[LockEventsResponse],
    responses=get_routers_responses()
)
def list_all_straight_bond_lock_events(
    data: dict = Depends(ListAllLockEvent(config.BOND_TOKEN_ENABLED))
):
    return json_response({
        **SuccessResponse.default(),
        "data": data
    })


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
        idx_token_model: IDXTokenModel
    ) -> None:
        self.token_enabled = token_enabled
        self.token_type = token_type
        self.token_model = token_model
        self.idx_token_model = idx_token_model

    def get_list(self, req: Request, request_query: ListAllPositionQuery, session: Session, account_address=None):

        # API Enabled Check
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.isAddress(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")
        enable_index = request_query.enable_index

        if enable_index:
            # If enable_index flag is set true, get position data from DB.
            data = self.get_list_from_index(
                request_query=request_query,
                session=session,
                account_address=account_address
            )
            return data

        # If enable_index flag is not set or set false, get position data from contract.
        data = self.get_list_from_contract(
            request_query=request_query,
            session=session,
            account_address=account_address
        )
        return data

    def get_list_from_index(self, request_query: ListAllPositionQuery, session: Session, account_address: str):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details
        query = session.query(Listing.token_address, IDXPosition, func.sum(IDXLockedPosition.value), self.idx_token_model). \
            join(self.idx_token_model, Listing.token_address == self.idx_token_model.token_address). \
            outerjoin(
                IDXPosition,
                and_(
                    Listing.token_address == IDXPosition.token_address,
                    IDXPosition.account_address == account_address
                )
            ). \
            outerjoin(
                IDXLockedPosition,
                and_(
                    Listing.token_address == IDXLockedPosition.token_address,
                    IDXLockedPosition.account_address == account_address
                )
            ). \
            filter(or_(
                IDXPosition.balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0
            )). \
            group_by(Listing.id, IDXPosition.id, self.idx_token_model.token_address, IDXLockedPosition.token_address). \
            order_by(Listing.id)

        total = query.count()
        count = total
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_position_list: list[tuple[str, IDXPosition, int | None, IDXTokenInstance]] = query.all()

        position_list = []
        for item in _token_position_list:
            position = {
                "balance": item[1].balance if item[1] and item[1].balance else 0,
                "pending_transfer": item[1].pending_transfer if item[1] and item[1].pending_transfer else 0,
                "exchange_balance": item[1].exchange_balance if item[1] and item[1].exchange_balance else 0,
                "exchange_commitment": item[1].exchange_commitment if item[1] and item[1].exchange_commitment else 0,
                "locked": item[2] if item[2] else 0
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
                "total": total
            },
            "positions": position_list
        }

    def get_list_from_contract(self, request_query: ListAllPositionQuery, session: Session, account_address: str):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details
        # Get TokenList Contract
        _list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=str(config.TOKEN_LIST_CONTRACT_ADDRESS)
        )

        # Get Listing Tokens
        _token_list = session.query(Listing). \
            order_by(Listing.id). \
            all()

        position_list = []
        limit_count = 0
        count = 0
        for _token in _token_list:
            token_info = Contract.call_function(
                contract=_list_contract,
                function_name="getTokenByAddress",
                args=(_token.token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            token_address = token_info[0]
            token_template = token_info[1]
            if token_template == self.token_type:

                # Get Position
                position = self._get_position(account_address, token_address, session, is_detail=include_token_details)

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
                "total": count
            },
            "positions": position_list
        }

    def get_one(self, req: Request, request_query: GetPositionQuery, session: Session, account_address: str, token_address: str):
        # API Enabled Check
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.url.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.isAddress(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")
        try:
            token_address = to_checksum_address(token_address)
            if not Web3.isAddress(token_address):
                raise InvalidParameterError(description="invalid contract_address")
        except:
            raise InvalidParameterError(description="invalid contract_address")
        enable_index = request_query.enable_index

        if enable_index:
            # If enable_index flag is set true, get position data from DB.
            data = self.get_one_from_index(
                session=session,
                account_address=account_address,
                token_address=token_address
            )
            return data
        # If enable_index flag is not set or set false, get position data from contract.
        data = self.get_one_from_contract(
            session=session,
            account_address=account_address,
            token_address=token_address
        )
        return data

    def get_one_from_index(self, session: Session, account_address: str, token_address: str):
        query = (
            session.query(Listing.token_address, IDXPosition, func.sum(IDXLockedPosition.value), self.idx_token_model).
            join(self.idx_token_model, Listing.token_address == self.idx_token_model.token_address).
            outerjoin(
                IDXPosition,
                and_(
                    Listing.token_address == IDXPosition.token_address,
                    IDXPosition.account_address == account_address
                )
            ).
            outerjoin(
                IDXLockedPosition,
                and_(
                    Listing.token_address == IDXLockedPosition.token_address,
                    IDXLockedPosition.account_address == account_address
                )
            ).
            filter(Listing.token_address == token_address).
            filter(or_(
                IDXPosition.balance != 0,
                IDXPosition.pending_transfer != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.exchange_commitment != 0,
                IDXLockedPosition.value != 0
            )).
            group_by(Listing.id, IDXPosition.id, self.idx_token_model.token_address, IDXLockedPosition.token_address)
        )
        result: tuple[str, IDXPosition | None, int | None, IDXTokenInstance] | None = query.first()
        if result is None:
            raise DataNotExistsError(description="contract_address: %s" % token_address)
        _position = result[1]
        _locked = result[2]
        token = result[3]

        return {
            "balance": _position.balance if _position and _position.balance else 0,
            "pending_transfer": _position.pending_transfer if _position and _position.pending_transfer else 0,
            "exchange_balance":_position.exchange_balance if _position and _position.exchange_balance else 0,
            "exchange_commitment": _position.exchange_commitment if _position and _position.exchange_commitment else 0,
            "locked": _locked or 0,
            "token": self.token_model.from_model(token).__dict__
        }

    def get_one_from_contract(
        self,
        session: Session,
        account_address: str,
        token_address: str
    ):
        # Get Listing Token
        _token = session.query(Listing). \
            filter(Listing.token_address == token_address). \
            first()
        if _token is None:
            raise DataNotExistsError(description="contract_address: %s" % token_address)

        # Get TokenList Contract
        _list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=str(config.TOKEN_LIST_CONTRACT_ADDRESS)
        )
        token_info = Contract.call_function(
            contract=_list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )
        token_template = token_info[1]
        if token_template != self.token_type:
            raise DataNotExistsError(description="contract_address: %s" % token_address)

        # Get Position
        position = self._get_position(account_address, token_address, session, is_detail=True)
        if position is None:
            raise DataNotExistsError(description="contract_address: %s" % token_address)

        return position

    def _get_position(self, account_address: str, token_address: str, session: Session, is_detail=False):

        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(account_address, token_address,),
                    default_returns=0
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
                    session=session,
                    token_address=token_address
                )
                position = {
                    "balance": balance,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except Exception as e:
            LOG.error(e)
            return None

    def _get_contract(self, token_address: str):

        # Get Token Contract
        _token_contract = Contract.get_contract(
            contract_name=self.token_type,
            address=token_address
        )

        # Get Exchange Contract
        exchange_address = Contract.call_function(
            contract=_token_contract,
            function_name="tradableExchange",
            args=(),
            default_returns=config.ZERO_ADDRESS
        )
        _exchange_contract = None
        if exchange_address != config.ZERO_ADDRESS:
            _exchange_contract = Contract.get_contract(
                contract_name="IbetExchangeInterface",
                address=exchange_address
            )

        return _token_contract, _exchange_contract


class BasePositionShare(BasePosition):
    def __init__(self):
        super().__init__(
            config.SHARE_TOKEN_ENABLED,
            "IbetShare",
            ShareToken,
            IDXShareToken
        )

    def _get_position(self, account_address: str, token_address: str, session: Session, is_detail=False):

        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0
            )
            pending_transfer = Contract.call_function(
                contract=_token_contract,
                function_name="pendingTransfer",
                args=(account_address,),
                default_returns=0
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0

            # If balance, pending_transfer, and commitment are non-zero,
            # get the token information from TokenContract.
            if balance == 0 and \
                    pending_transfer == 0 and \
                    _exchange_balance == 0 and \
                    _exchange_commitment == 0:
                return None
            else:
                token = ShareToken.get(
                    session=session,
                    token_address=token_address
                )
                position = {
                    "balance": balance,
                    "pending_transfer": pending_transfer,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                    "locked": None
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except Exception as e:
            LOG.error(e)
            return None


class BasePositionStraightBond(BasePosition):
    def __init__(self):
        super().__init__(
            config.BOND_TOKEN_ENABLED,
            "IbetStraightBond",
            BondToken,
            IDXBondToken
        )

    def _get_position(self, account_address: str, token_address: str, session: Session, is_detail=False):

        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0
            )
            pending_transfer = Contract.call_function(
                contract=_token_contract,
                function_name="pendingTransfer",
                args=(account_address,),
                default_returns=0
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0

            # If balance, pending_transfer, and commitment are non-zero,
            # get the token information from TokenContract.
            if balance == 0 and \
                    pending_transfer == 0 and \
                    _exchange_balance == 0 and \
                    _exchange_commitment == 0:
                return None
            else:
                token = BondToken.get(
                    session=session,
                    token_address=token_address
                )
                position = {
                    "balance": balance,
                    "pending_transfer": pending_transfer,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                    "locked": None
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except Exception as e:
            LOG.error(e)
            return None


class BasePositionMembership(BasePosition):
    def __init__(self):
        super().__init__(
            config.MEMBERSHIP_TOKEN_ENABLED,
            "IbetMembership",
            MembershipToken,
            IDXMembershipToken
        )

    def get_list_from_index(self, request_query: ListAllPositionQuery, session: Session, account_address: str):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details
        query = session.query(Listing.token_address, IDXPosition, self.idx_token_model). \
            join(self.idx_token_model, Listing.token_address == self.idx_token_model.token_address). \
            join(IDXPosition, Listing.token_address == IDXPosition.token_address). \
            filter(IDXPosition.account_address == account_address). \
            filter(or_(
                IDXPosition.balance != 0,
                IDXPosition.exchange_balance != 0,
                IDXPosition.exchange_commitment != 0
            )). \
            order_by(Listing.id)

        total = query.count()
        count = total
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_position_list: list[tuple[str, IDXPosition, IDXTokenInstance]] = query.all()

        position_list = []
        for item in _token_position_list:
            position = {
                "balance": item[1].balance if item[1] and item[1].balance else 0,
                "exchange_balance": item[1].exchange_balance if item[1] and item[1].exchange_balance else 0,
                "exchange_commitment": item[1].exchange_commitment if item[1] and item[1].exchange_commitment else 0,
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
                "total": total
            },
            "positions": position_list
        }


class BasePositionCoupon(BasePosition):

    def __init__(self):
        super().__init__(
            config.COUPON_TOKEN_ENABLED,
            "IbetCoupon",
            CouponToken,
            IDXCouponToken
        )

    def get_list_from_index(self, request_query: ListAllPositionQuery, session: Session, account_address: str):
        offset = request_query.offset
        limit = request_query.limit
        include_token_details = request_query.include_token_details

        # NOTE: Sub Query for sum of used amount
        sub_tx_used = (
            session.query(
                sum_(IDXConsumeCoupon.amount).label("used"),
                IDXConsumeCoupon.token_address,
                IDXConsumeCoupon.account_address
            ).
            filter(IDXConsumeCoupon.account_address == account_address).
            group_by(
                IDXConsumeCoupon.token_address,
                IDXConsumeCoupon.account_address
            ).
            subquery("sub_tx_used")
        )
        query = (
            session.query(Listing.token_address, IDXPosition, self.idx_token_model, sub_tx_used.c.used).
            join(
                self.idx_token_model,
                Listing.token_address == self.idx_token_model.token_address
            ).
            outerjoin(IDXPosition, and_(
                Listing.token_address == IDXPosition.token_address,
                IDXPosition.account_address == account_address
            )).
            outerjoin(sub_tx_used, and_(
                Listing.token_address == sub_tx_used.c.token_address,
                sub_tx_used.c.account_address == account_address
            )).
            filter(
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.exchange_commitment != 0,
                    sub_tx_used.c.used != 0,
                    session.query(IDXTransfer).filter(
                        and_(
                            IDXTransfer.token_address == Listing.token_address,
                            IDXTransfer.to_address == account_address
                        )
                    ).exists()
                )
            ).order_by(Listing.id)
        )

        total = query.count()
        count = total
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_position_list: list[tuple[str, IDXPosition, IDXTokenInstance, Decimal | None]] = query.all()

        position_list = []
        for item in _token_position_list:
            if item[1] is None:
                position = {
                    "balance": 0,
                    "exchange_balance": 0,
                    "exchange_commitment": 0,
                    "used": int(item[3]) if item[3] else 0
                }
            else:
                position = {
                    "balance": item[1].balance or 0,
                    "exchange_balance": item[1].exchange_balance or 0,
                    "exchange_commitment": item[1].exchange_commitment or 0,
                    "used": int(item[3]) if item[3] else 0
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
                "total": total
            },
            "positions": position_list
        }

    def _get_position(self, account_address, token_address, session, is_detail=False):

        # Get Contract
        _token_contract, _exchange_contract = self._get_contract(token_address)

        try:
            balance = Contract.call_function(
                contract=_token_contract,
                function_name="balanceOf",
                args=(account_address,),
                default_returns=0
            )
            used = Contract.call_function(
                contract=_token_contract,
                function_name="usedOf",
                args=(account_address,),
                default_returns=0
            )
            if _exchange_contract is not None:
                _exchange_balance = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="balanceOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
                _exchange_commitment = Contract.call_function(
                    contract=_exchange_contract,
                    function_name="commitmentOf",
                    args=(account_address, token_address,),
                    default_returns=0
                )
            else:
                # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                _exchange_balance = 0
                _exchange_commitment = 0

            # Retrieving token receipt history from IDXTransfer
            # NOTE: Index data has a lag from the most recent transfer state.
            received_history = session.query(IDXTransfer). \
                filter(IDXTransfer.token_address == token_address). \
                filter(IDXTransfer.to_address == account_address). \
                first()
            # If balance, commitment, and used are non-zero, and exist received history,
            # get the token information from TokenContract.
            if balance == 0 and \
                    _exchange_balance == 0 and \
                    _exchange_commitment == 0 and \
                    used == 0 and \
                    received_history is None:
                return None
            else:
                token = CouponToken.get(
                    session=session,
                    token_address=token_address
                )
                position = {
                    "balance": balance,
                    "exchange_balance": _exchange_balance,
                    "exchange_commitment": _exchange_commitment,
                    "used": used
                }
                if is_detail is True:
                    position["token"] = token.__dict__
                else:
                    position["token_address"] = token_address
                return position
        except Exception as e:
            LOG.error(e)
            return None


BasePositionType = Union[
    Type[BasePositionStraightBond] |
    Type[BasePositionShare] |
    Type[BasePositionMembership] |
    Type[BasePositionCoupon]
]


class GetPositionList:
    base_position: BasePositionType

    def __init__(self, base_position: BasePositionType):
        self.base_position = base_position

    def __call__(
        self,
        req: Request,
        account_address: str = Path(),
        request_query: ListAllPositionQuery = Depends(),
        session: Session = Depends(db_session)
    ):
        return self.base_position().get_list(req, request_query, session, account_address)


class GetPosition:
    base_position: BasePositionType

    def __init__(self, base_position: BasePositionType):
        self.base_position = base_position

    def __call__(
        self,
        req: Request,
        request_query: GetPositionQuery = Depends(),
        account_address: str = Path(),
        token_address: str = Path(),
        session: Session = Depends(db_session)
    ):
        return self.base_position().get_one(req, request_query, session, account_address, token_address)


# ------------------------------
# Position List(Share)
# ------------------------------
@router.get(
    "/{account_address}/Share",
    summary="Share Token Position",
    operation_id="GetShareTokenPosition",
    response_model=GenericSuccessResponse[GenericSecurityTokenPositionsResponse[RetrieveShareTokenResponse]],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def list_all_share_positions(
    positions: Union[
        list[SecurityTokenPositionWithDetail],
        list[SecurityTokenPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionShare))
):
    """
    Endpoint: /Position/{account_address}/Share
    """
    return json_response({
        **SuccessResponse.default(),
        "data": positions
    })


# ------------------------------
# Position List(StraightBond)
# ------------------------------
@router.get(
    "/{account_address}/StraightBond",
    summary="StraightBond Token Position",
    operation_id="GetStraightBondTokenPosition",
    response_model=GenericSuccessResponse[GenericSecurityTokenPositionsResponse[RetrieveStraightBondTokenResponse]],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def list_all_straight_bond_positions(
    positions: Union[
        list[SecurityTokenPositionWithDetail],
        list[SecurityTokenPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionStraightBond))
):
    """
    Endpoint: /Position/{account_address}/StraightBond
    """
    return json_response({
        **SuccessResponse.default(),
        "data": positions
    })


# ------------------------------
# Position List(Membership)
# ------------------------------
@router.get(
    "/{account_address}/Membership",
    summary="Membership Token Position",
    operation_id="GetMembershipTokenPosition",
    response_model=GenericSuccessResponse[MembershipPositionsResponse],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def list_all_membership_positions(
    positions: Union[
        list[MembershipPositionWithDetail],
        list[MembershipPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionMembership))
):
    """
    Endpoint: /Position/{account_address}/Membership
    """
    return json_response({
        **SuccessResponse.default(),
        "data": positions
    })


# ------------------------------
# Position List(Coupon)
# ------------------------------
@router.get(
    "/{account_address}/Coupon",
    summary="Coupon Token Position",
    operation_id="GetCouponTokenPosition",
    response_model=GenericSuccessResponse[CouponPositionsResponse],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def list_all_coupon_positions(
    positions: Union[
        list[CouponPositionWithDetail],
        list[CouponPositionWithAddress]
    ] = Depends(GetPositionList(BasePositionCoupon))
):
    """
    Endpoint: /Position/{account_address}/Coupon
    """
    return json_response({
        **SuccessResponse.default(),
        "data": positions
    })


# ------------------------------
# Get Position(Share)
# ------------------------------
@router.get(
    "/{account_address}/Share/{token_address}",
    summary="Share Token Position By Token Address",
    operation_id="GetShareTokenPositionByAddress",
    response_model=GenericSuccessResponse[SecurityTokenPositionWithDetail[RetrieveShareTokenResponse]],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def retrieve_share_position_by_token_address(
    position: SecurityTokenPositionWithDetail = Depends(GetPosition(BasePositionShare))
):
    """
    Endpoint: /Position/{account_address}/Share/{contract_address}
    """
    return json_response({
        **SuccessResponse.default(),
        "data": position
    })


# ------------------------------
# Get Position(StraightBond)
# ------------------------------
@router.get(
    "/{account_address}/StraightBond/{token_address}",
    summary="StraightBond Token Position By Token Address",
    operation_id="GetStraightBondTokenPositionByAddress",
    response_model=GenericSuccessResponse[SecurityTokenPositionWithDetail[RetrieveStraightBondTokenResponse]],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def retrieve_straight_bond_position_by_token_address(
    position: SecurityTokenPositionWithDetail = Depends(GetPosition(BasePositionStraightBond))
):
    """
    Endpoint: /Position/{account_address}/StraightBond/{contract_address}
    """
    return json_response({
        **SuccessResponse.default(),
        "data": position
    })


# ------------------------------
# Get Position(Membership)
# ------------------------------
@router.get(
    "/{account_address}/Membership/{token_address}",
    summary="Membership Token Position By Token Address",
    operation_id="GetMembershipTokenPositionByAddress",
    response_model=GenericSuccessResponse[MembershipPositionWithDetail],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def retrieve_membership_position_by_token_address(
    position: MembershipPositionWithDetail = Depends(GetPosition(BasePositionMembership))
):
    """
    Endpoint: /Position/{account_address}/Membership/{contract_address}
    """
    return json_response({
        **SuccessResponse.default(),
        "data": position
    })


# ------------------------------
# Get Position(Coupon)
# ------------------------------
@router.get(
    "/{account_address}/Coupon/{token_address}",
    summary="Coupon Token Position By Token Address",
    operation_id="GetCouponTokenPositionByAddress",
    response_model=GenericSuccessResponse[CouponPositionWithDetail],
    responses=get_routers_responses(DataNotExistsError, NotSupportedError, InvalidParameterError)
)
def retrieve_coupon_position_by_token_address(
    position: CouponPositionWithDetail = Depends(GetPosition(BasePositionCoupon))
):
    """
    Endpoint: /Position/{account_address}/Coupon/{contract_address}
    """
    return json_response({
        **SuccessResponse.default(),
        "data": position
    })
