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
from cerberus import Validator
from eth_utils import to_checksum_address
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
    IDXTransfer
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
        offset = request_json["offset"]
        limit = request_json["limit"]

        session = req.context["session"]

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
                position = self._get_position(account_address, token_address, session)

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

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": count
            },
            "positions": position_list
        }
        self.on_success(res, data)

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
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
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


class BasePositionCoupon(BasePosition):

    def __init__(self):
        self.token_enabled = config.SHARE_TOKEN_ENABLED
        self.token_type = "IbetCoupon"
        self.token_model = CouponToken

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
        LOG.info('v3.position.PositionShare(GET)')
        super().on_get_list(req, res, account_address)


# ------------------------------
# Position List(StraightBond)
# ------------------------------
class PositionStraightBond(BasePositionStraightBond):
    """
    Endpoint: /Position/{account_address}/StraightBond
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        LOG.info('v3.position.PositionStraightBond(GET)')
        super().on_get_list(req, res, account_address)


# ------------------------------
# Position List(Membership)
# ------------------------------
class PositionMembership(BasePositionMembership):
    """
    Endpoint: /Position/{account_address}/Membership
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        LOG.info('v3.position.PositionMembership(GET)')
        super().on_get_list(req, res, account_address)


# ------------------------------
# Position List(Coupon)
# ------------------------------
class PositionCoupon(BasePositionCoupon):
    """
    Endpoint: /Position/{account_address}/Coupon
    """

    def on_get(self, req, res, account_address=None, **kwargs):
        LOG.info('v3.position.PositionCoupon(GET)')
        super().on_get_list(req, res, account_address)


# ------------------------------
# Get Position(Share)
# ------------------------------
class PositionShareContractAddress(BasePositionShare):
    """
    Endpoint: /Position/{account_address}/Share/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        LOG.info('v3.position.PositionShareContractAddress(GET)')
        super().on_get_from_contract_address(req, res, account_address, contract_address)


# ------------------------------
# Get Position(StraightBond)
# ------------------------------
class PositionStraightBondContractAddress(BasePositionStraightBond):
    """
    Endpoint: /Position/{account_address}/StraightBond/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        LOG.info('v3.position.PositionStraightBondContractAddress(StraightBond)')
        super().on_get_from_contract_address(req, res, account_address, contract_address)


# ------------------------------
# Get Position(Membership)
# ------------------------------
class PositionMembershipContractAddress(BasePositionMembership):
    """
    Endpoint: /Position/{account_address}/Membership/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        LOG.info('v3.position.PositionMembershipContractAddress(GET)')
        super().on_get_from_contract_address(req, res, account_address, contract_address)


# ------------------------------
# Get Position(Coupon)
# ------------------------------
class PositionCouponContractAddress(BasePositionCoupon):
    """
    Endpoint: /Position/{account_address}/Coupon/{contract_address}
    """

    def on_get(self, req, res, account_address=None, contract_address=None):
        LOG.info('v3.position.PositionCouponContractAddress(GET)')
        super().on_get_from_contract_address(req, res, account_address, contract_address)
