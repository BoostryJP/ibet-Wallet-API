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
from cerberus import Validator
from eth_utils import to_checksum_address
from sqlalchemy import (
    or_,
    and_
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
from app.api.common import BaseResource
from app.contracts import Contract
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
    IDXMembershipToken
)
from app.model.blockchain import (
    ShareToken,
    BondToken,
    MembershipToken,
    CouponToken
)

LOG = log.get_logger()


class BasePosition(BaseResource):
    # NOTE: Set Child class initializer.
    token_enabled: bool
    token_type: str
    token_model: Union[Type[ShareToken], Type[BondToken], Type[MembershipToken], Type[CouponToken]]
    idx_token_model: IDXTokenModel
    exchange_contract_name: str

    def on_get_list(self, req, res, account_address=None):

        # API Enabled Check
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.isAddress(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")
        request_json = BasePosition.validate(req)
        enable_index = True if request_json["enable_index"] == "true" else False

        session = req.context["session"]

        if enable_index:
            # If enable_index flag is set true, get position data from DB.
            data = self.on_get_list_from_index(
                request_json=request_json,
                session=session,
                account_address=account_address
            )
            self.on_success(res, data)
            return

        # If enable_index flag is not set or set false, get position data from contract.
        data = self.on_get_list_from_contract(
            request_json=request_json,
            session=session,
            account_address=account_address
        )
        self.on_success(res, data)

    def on_get_list_from_index(self, request_json: dict, session: Session, account_address: str):
        offset = request_json["offset"]
        limit = request_json["limit"]
        include_token_details = True if request_json["include_token_details"] == "true" else False
        query = session.query(Listing.token_address, IDXPosition, self.idx_token_model). \
            join(self.idx_token_model, Listing.token_address == self.idx_token_model.token_address). \
            join(IDXPosition, Listing.token_address == IDXPosition.token_address). \
            filter(IDXPosition.account_address == account_address). \
            filter(or_(
                IDXPosition.balance != 0,
                IDXPosition.pending_transfer != 0,
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
                "pending_transfer": item[1].pending_transfer if item[1] and item[1].pending_transfer else 0,
                "exchange_balance": item[1].exchange_balance if item[1] and item[1].exchange_balance else 0,
                "exchange_commitment": item[1].exchange_commitment if item[1] and item[1].exchange_commitment else 0
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

    def on_get_list_from_contract(self, request_json: dict, session: Session, account_address: str):
        offset = request_json["offset"]
        limit = request_json["limit"]
        include_token_details = True if request_json["include_token_details"] == "true" else False
        # Get TokenList Contract
        _list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
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

    def on_get_from_contract_address(self, req, res, account_address=None, contract_address=None):

        # API Enabled Check
        if self.token_enabled is False:
            raise NotSupportedError(method="GET", url=req.path)

        # Validation
        try:
            account_address = to_checksum_address(account_address)
            if not Web3.isAddress(account_address):
                raise InvalidParameterError(description="invalid account_address")
        except:
            raise InvalidParameterError(description="invalid account_address")
        try:
            token_address = to_checksum_address(contract_address)
            if not Web3.isAddress(token_address):
                raise InvalidParameterError(description="invalid contract_address")
        except:
            raise InvalidParameterError(description="invalid contract_address")

        session = req.context["session"]

        # Get Listing Token
        _token = session.query(Listing). \
            filter(Listing.token_address == token_address). \
            first()
        if _token is None:
            raise DataNotExistsError(description="contract_address: %s" % contract_address)

        # Get TokenList Contract
        _list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )
        token_info = Contract.call_function(
            contract=_list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )
        token_template = token_info[1]
        if token_template != self.token_type:
            raise DataNotExistsError(description="contract_address: %s" % contract_address)

        # Get Position
        position = self._get_position(account_address, token_address, session, is_detail=True)
        if position is None:
            raise DataNotExistsError(description="contract_address: %s" % contract_address)

        self.on_success(res, position)

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

    def _get_contract(self, token_address):

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

    @staticmethod
    def validate(req):
        request_json = {
            "include_token_details": req.get_param("include_token_details"),
            "enable_index": req.get_param("enable_index"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "include_token_details": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["true", "false"],
            },
            "enable_index": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["true", "false"],
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            'limit': {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


class BasePositionShare(BasePosition):

    def __init__(self):
        self.token_enabled = config.SHARE_TOKEN_ENABLED
        self.token_type = "IbetShare"
        self.token_model = ShareToken
        self.idx_token_model = IDXShareToken

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


class BasePositionStraightBond(BasePosition):

    def __init__(self):
        self.token_enabled = config.SHARE_TOKEN_ENABLED
        self.token_type = "IbetStraightBond"
        self.token_model = BondToken
        self.idx_token_model = IDXBondToken

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


class BasePositionMembership(BasePosition):
    def __init__(self):
        self.token_enabled = config.SHARE_TOKEN_ENABLED
        self.token_type = "IbetMembership"
        self.token_model = MembershipToken
        self.idx_token_model = IDXMembershipToken

    def on_get_list_from_index(self, request_json: dict, session: Session, account_address: str):
        offset = request_json["offset"]
        limit = request_json["limit"]
        include_token_details = True if request_json["include_token_details"] == "true" else False
        query = session.query(Listing.token_address, IDXPosition, self.idx_token_model).\
            join(self.idx_token_model, Listing.token_address == self.idx_token_model.token_address).\
            join(IDXPosition, Listing.token_address == IDXPosition.token_address).\
            filter(IDXPosition.account_address == account_address).filter(
                or_(
                    IDXPosition.balance != 0,
                    IDXPosition.exchange_balance != 0,
                    IDXPosition.exchange_commitment != 0
                )
            ).order_by(Listing.id)

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
        self.token_enabled = config.SHARE_TOKEN_ENABLED
        self.token_type = "IbetCoupon"
        self.token_model = CouponToken
        self.idx_token_model = IDXCouponToken

    def on_get_list_from_index(self, request_json: dict, session: Session, account_address: str):
        offset = request_json["offset"]
        limit = request_json["limit"]
        include_token_details = True if request_json["include_token_details"] == "true" else False

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


# ------------------------------
# Position List(Share)
# ------------------------------
class PositionShare(BasePositionShare):
    """
    Endpoint: /Position/{account_address}/Share
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        super().on_get_list(req, res, account_address)


# ------------------------------
# Position List(StraightBond)
# ------------------------------
class PositionStraightBond(BasePositionStraightBond):
    """
    Endpoint: /Position/{account_address}/StraightBond
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        super().on_get_list(req, res, account_address)


# ------------------------------
# Position List(Membership)
# ------------------------------
class PositionMembership(BasePositionMembership):
    """
    Endpoint: /Position/{account_address}/Membership
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        super().on_get_list(req, res, account_address)


# ------------------------------
# Position List(Coupon)
# ------------------------------
class PositionCoupon(BasePositionCoupon):
    """
    Endpoint: /Position/{account_address}/Coupon
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        super().on_get_list(req, res, account_address)


# ------------------------------
# Get Position(Share)
# ------------------------------
class PositionShareContractAddress(BasePositionShare):
    """
    Endpoint: /Position/{account_address}/Share/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        super().on_get_from_contract_address(req, res, account_address, contract_address)


# ------------------------------
# Get Position(StraightBond)
# ------------------------------
class PositionStraightBondContractAddress(BasePositionStraightBond):
    """
    Endpoint: /Position/{account_address}/StraightBond/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        super().on_get_from_contract_address(req, res, account_address, contract_address)


# ------------------------------
# Get Position(Membership)
# ------------------------------
class PositionMembershipContractAddress(BasePositionMembership):
    """
    Endpoint: /Position/{account_address}/Membership/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        super().on_get_from_contract_address(req, res, account_address, contract_address)


# ------------------------------
# Get Position(Coupon)
# ------------------------------
class PositionCouponContractAddress(BasePositionCoupon):
    """
    Endpoint: /Position/{account_address}/Coupon/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        super().on_get_from_contract_address(req, res, account_address, contract_address)
