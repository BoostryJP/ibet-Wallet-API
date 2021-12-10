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
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    NotSupportedError
)
from app import config
from app.contracts import Contract
from app.model.db import (
    Listing,
    IDXConsumeCoupon,
    IDXTransfer
)
from app.model.blockchain import (
    BondToken,
    ShareToken,
    MembershipToken,
    CouponToken
)

LOG = log.get_logger()


# /Position/Share
class ShareMyTokens(BaseResource):
    """保有一覧参照（Share）"""

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.position.ShareMyTokens")

        session = req.context["session"]

        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method="POST", url=req.path)

        # Validation
        request_json = ShareMyTokens.validate(req)

        # TokenList Contract
        list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Exchange Contract
        _exchange_contract = None
        if config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS is not None:
            _exchange_contract = Contract.get_contract(
                contract_name="IbetExchangeInterface",
                address=config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS
            )

        listed_tokens = session.query(Listing).all()
        position_list = []
        for _account_address in request_json["account_address_list"]:
            # Get token details
            for token in listed_tokens:
                token_info = Contract.call_function(
                    contract=list_contract,
                    function_name="getTokenByAddress",
                    args=(token.token_address,),
                    default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
                )
                token_address = token_info[0]
                token_template = token_info[1]
                if token_template == "IbetShare":
                    _account_address = to_checksum_address(_account_address)
                    _token_contract = Contract.get_contract(
                        contract_name="IbetShare",
                        address=token_address
                    )
                    try:
                        balance = Contract.call_function(
                            contract=_token_contract,
                            function_name="balanceOf",
                            args=(_account_address,),
                            default_returns=0
                        )
                        pending_transfer = Contract.call_function(
                            contract=_token_contract,
                            function_name="pendingTransfer",
                            args=(_account_address,),
                            default_returns=0
                        )
                        if _exchange_contract is not None:
                            _exchange_balance = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="balanceOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                            _exchange_commitment = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="commitmentOf",
                                args=(_account_address, token_address,),
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
                            continue
                        else:
                            sharetoken = ShareToken.get(
                                session=session,
                                token_address=token_address
                            )
                            position_list.append({
                                "token": sharetoken.__dict__,
                                "balance": balance,
                                "exchange_balance": _exchange_balance,
                                "exchange_commitment": _exchange_commitment,
                                "pending_transfer": pending_transfer
                            })
                    except Exception as e:
                        LOG.exception(e)
                        continue

        self.on_success(res, position_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            }
        })
        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError("invalid account address")

        return request_json


# /Position/StraightBond
class StraightBondMyTokens(BaseResource):
    """保有一覧参照（StraightBond）"""

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.position.StraightBondMyTokens")

        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method="POST", url=req.path)

        # Validation
        request_json = StraightBondMyTokens.validate(req)

        # TokenList Contract
        list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Bond Exchange Contract
        _exchange_contract = None
        if config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS is not None:
            _exchange_contract = Contract.get_contract(
                contract_name="IbetExchangeInterface",
                address=config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS
            )

        listed_tokens = session.query(Listing).all()
        position_list = []
        for _account_address in request_json["account_address_list"]:
            # Get token details
            for token in listed_tokens:
                token_info = Contract.call_function(
                    contract=list_contract,
                    function_name="getTokenByAddress",
                    args=(token.token_address,),
                    default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
                )
                token_address = token_info[0]
                token_template = token_info[1]
                if token_template == "IbetStraightBond":
                    _account_address = to_checksum_address(_account_address)
                    _token_contract = Contract.get_contract(
                        contract_name="IbetStraightBond",
                        address=token_address
                    )
                    try:
                        balance = Contract.call_function(
                            contract=_token_contract,
                            function_name="balanceOf",
                            args=(_account_address,),
                            default_returns=0
                        )
                        pending_transfer = Contract.call_function(
                            contract=_token_contract,
                            function_name="pendingTransfer",
                            args=(_account_address,),
                            default_returns=0
                        )
                        if _exchange_contract is not None:
                            _exchange_balance = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="balanceOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                            _exchange_commitment = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="commitmentOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                        else:
                            # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                            _exchange_balance = 0
                            _exchange_commitment = 0
                        # If balance and commitment are non-zero,
                        # get the token information from TokenContract.
                        if balance == 0 and \
                                pending_transfer == 0 and \
                                _exchange_balance == 0 and \
                                _exchange_commitment == 0:
                            continue
                        else:
                            bondtoken = BondToken.get(
                                session=session,
                                token_address=token_address
                            )
                            position_list.append({
                                "token": bondtoken.__dict__,
                                "balance": balance,
                                "exchange_balance": _exchange_balance,
                                "exchange_commitment": _exchange_commitment,
                                "pending_transfer": pending_transfer
                            })
                    except Exception as e:
                        LOG.error(e)
                        continue

        self.on_success(res, position_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json


# /Position/Membership
class MembershipMyTokens(BaseResource):
    """保有一覧参照（Membership）"""

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.position.MembershipMyTokens")

        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method="POST", url=req.path)

        # Validation
        request_json = MembershipMyTokens.validate(req)

        # TokenList Contract
        list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Exchange Contract
        _exchange_contract = None
        if config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS is not None:
            _exchange_contract = Contract.get_contract(
                contract_name="IbetExchangeInterface",
                address=config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS
            )

        listed_tokens = session.query(Listing).all()
        position_list = []
        for _account_address in request_json["account_address_list"]:
            # Get token details
            for token in listed_tokens:
                token_info = Contract.call_function(
                    contract=list_contract,
                    function_name="getTokenByAddress",
                    args=(token.token_address,),
                    default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
                )
                token_address = token_info[0]
                token_template = token_info[1]
                if token_template == "IbetMembership":
                    _account_address = to_checksum_address(_account_address)
                    _token_contract = Contract.get_contract(
                        contract_name="IbetMembership",
                        address=token_address
                    )
                    try:
                        balance = Contract.call_function(
                            contract=_token_contract,
                            function_name="balanceOf",
                            args=(_account_address,),
                            default_returns=0
                        )
                        if _exchange_contract is not None:
                            _exchange_balance = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="balanceOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                            _exchange_commitment = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="commitmentOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                        else:
                            # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                            _exchange_balance = 0
                            _exchange_commitment = 0
                        # If balance and commitment are non-zero,
                        # get the token information from TokenContract.
                        if balance == 0 and _exchange_balance == 0 and _exchange_commitment == 0:
                            continue
                        else:
                            membershiptoken = MembershipToken.get(
                                session=session,
                                token_address=token_address
                            )
                            position_list.append({
                                "token": membershiptoken.__dict__,
                                "balance": balance,
                                "exchange_balance": _exchange_balance,
                                "exchange_commitment": _exchange_commitment,
                            })
                    except Exception as e:
                        LOG.error(e)
                        continue

        self.on_success(res, position_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json


# /Position/Coupon
class CouponMyTokens(BaseResource):
    """保有一覧参照（Coupon）"""

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.position.CouponMyTokens")

        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method="POST", url=req.path)

        # Validation
        request_json = CouponMyTokens.validate(req)

        # TokenList Contract
        list_contract = Contract.get_contract(
            contract_name="TokenList",
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Coupon Exchange Contract
        _exchange_contract = None
        if config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS is not None:
            _exchange_contract = Contract.get_contract(
                contract_name="IbetExchangeInterface",
                address=config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS
            )

        listed_tokens = session.query(Listing).all()
        position_list = []
        for _account_address in request_json["account_address_list"]:
            # Get token details
            for token in listed_tokens:
                token_info = Contract.call_function(
                    contract=list_contract,
                    function_name="getTokenByAddress",
                    args=(token.token_address,),
                    default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
                )
                token_address = token_info[0]
                token_template = token_info[1]
                if token_template == "IbetCoupon":
                    _account_address = to_checksum_address(_account_address)
                    _token_contract = Contract.get_contract(
                        contract_name="IbetCoupon",
                        address=token_address
                    )
                    try:
                        balance = Contract.call_function(
                            contract=_token_contract,
                            function_name="balanceOf",
                            args=(_account_address,),
                            default_returns=0
                        )
                        if _exchange_contract is not None:
                            _exchange_balance = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="balanceOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                            _exchange_commitment = Contract.call_function(
                                contract=_exchange_contract,
                                function_name="commitmentOf",
                                args=(_account_address, token_address,),
                                default_returns=0
                            )
                        else:
                            # If EXCHANGE_CONTRACT_ADDRESS is not set, set commitment to zero.
                            _exchange_balance = 0
                            _exchange_commitment = 0

                        used = Contract.call_function(
                            contract=_token_contract,
                            function_name="usedOf",
                            args=(_account_address,),
                            default_returns=0
                        )
                        # Retrieving token receipt history from IDXTransfer
                        # NOTE: Index data has a lag from the most recent transfer state.
                        received_history = session.query(IDXTransfer). \
                            filter(IDXTransfer.token_address == token.token_address). \
                            filter(IDXTransfer.to_address == _account_address). \
                            first()
                        # If balance, commitment, and used are non-zero, and exist received history,
                        # get the token information from TokenContract.
                        if balance == 0 and \
                                _exchange_balance == 0 and \
                                _exchange_commitment == 0 and \
                                used == 0 and \
                                received_history is None:
                            continue
                        else:
                            coupontoken = CouponToken.get(
                                session=session,
                                token_address=token_address
                            )
                            position_list.append({
                                "token": coupontoken.__dict__,
                                "balance": balance,
                                "exchange_balance": _exchange_balance,
                                "exchange_commitment": _exchange_commitment,
                                "used": used
                            })
                    except Exception as e:
                        LOG.error(e)
                        continue

        self.on_success(res, position_list)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json


# /Position/Coupon/Consumptions
class CouponConsumptions(BaseResource):
    """Coupon消費履歴参照"""

    def on_post(self, req, res, **kwargs):
        LOG.info("v2.position.CouponConsumptions")
        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method="POST", url=req.path)

        # Validation
        request_json = CouponConsumptions.validate(req)

        # Create a list of coupon consumption history
        _coupon_address = to_checksum_address(request_json["token_address"])
        coupon_consumptions = []
        for _account_address in request_json["account_address_list"]:
            consumptions = session.query(IDXConsumeCoupon). \
                filter(IDXConsumeCoupon.token_address == _coupon_address). \
                filter(IDXConsumeCoupon.account_address == _account_address). \
                all()
            for consumption in consumptions:
                coupon_consumptions.append({
                    "account_address": _account_address,
                    "block_timestamp": consumption.block_timestamp.strftime("%Y/%m/%d %H:%M:%S"),
                    "value": consumption.amount
                })

        # Sort by block_timestamp in ascending order
        coupon_consumptions = sorted(
            coupon_consumptions,
            key=lambda x: x["block_timestamp"]
        )

        self.on_success(res, coupon_consumptions)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "token_address": {
                "type": "string",
                "empty": False,
                "required": True
            },
            "account_address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "empty": False,
                "required": True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        if not Web3.isAddress(request_json["token_address"]):
            raise InvalidParameterError

        for account_address in request_json["account_address_list"]:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json
