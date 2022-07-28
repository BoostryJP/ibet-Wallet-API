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
from falcon import Request
from sqlalchemy import (
    desc,
)
from typing import Optional

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    NotSupportedError
)
from app import config
from app.model.blockchain import (
    BondToken,
    ShareToken,
    CouponToken,
    MembershipToken
)
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Listing,
    IDXBondToken,
    IDXShareToken,
    IDXMembershipToken,
    IDXCouponToken
)

LOG = log.get_logger()


class StraightBondTokens(BaseResource):
    """
    Endpoint: /v3/Token/StraightBond
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = StraightBondTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        personal_info_address: Optional[str] = request_json.get("personal_info_address")
        transferable: Optional[bool] = request_json.get("transferable", None)
        is_offering: Optional[bool] = request_json.get("is_offering", None)
        transfer_approval_required: Optional[bool] = request_json.get("transfer_approval_required", None)
        is_redeemed: Optional[bool] = request_json.get("is_redeemed", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXBondToken).\
            join(Listing, Listing.token_address == IDXBondToken.token_address).\
            filter(Listing.is_public == True)
        if len(request_json["address_list"]) > 0:
            query = query.filter(IDXBondToken.token_address.in_(request_json["address_list"]))
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXBondToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXBondToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXBondToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXBondToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXBondToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXBondToken.status == status)
        if personal_info_address is not None:
            query = query.filter(IDXBondToken.personal_info_address == personal_info_address)
        if transferable is not None:
            query = query.filter(IDXBondToken.transferable == transferable)
        if is_offering is not None:
            query = query.filter(IDXBondToken.is_offering == is_offering)
        if transfer_approval_required is not None:
            query = query.filter(IDXBondToken.transfer_approval_required == transfer_approval_required)
        if is_redeemed is not None:
            query = query.filter(IDXBondToken.is_redeemed == is_redeemed)
        count = query.count()

        sort_attr = getattr(IDXBondToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXBondToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXBondToken] = query.all()
        tokens = []

        for _token in _token_list:
            tokens.append(BondToken.from_model(_token).__dict__)

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "tokens": tokens
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "address_list": req.get_param_as_list("address_list", default=[]),
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "personal_info_address": req.get_param("personal_info_address"),
            "transferable": req.get_param_as_bool("transferable"),
            "is_offering": req.get_param_as_bool("is_offering"),
            "transfer_approval_required": req.get_param_as_bool("transfer_approval_required"),
            "is_redeemed": req.get_param_as_bool("is_redeemed"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False,
                "nullable": False,
            },
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "personal_info_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_offering": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transfer_approval_required": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_redeemed": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "token_address",
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "personal_info_address",
                    "transferable",
                    "is_offering",
                    "transfer_approval_required",
                    "is_redeemed"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
        })

        for address in request_json["address_list"]:
            try:
                to_checksum_address(address)
            except ValueError:
                description = f"invalid token_address: {address}"
                raise InvalidParameterError(description=description)

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


class StraightBondTokenAddresses(BaseResource):
    """
    Endpoint: /v3/Token/StraightBond/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = StraightBondTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        personal_info_address: Optional[str] = request_json.get("personal_info_address")
        transferable: Optional[bool] = request_json.get("transferable", None)
        is_offering: Optional[bool] = request_json.get("is_offering", None)
        transfer_approval_required: Optional[bool] = request_json.get("transfer_approval_required", None)
        is_redeemed: Optional[bool] = request_json.get("is_redeemed", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXBondToken).\
            join(Listing, Listing.token_address == IDXBondToken.token_address).\
            filter(Listing.is_public == True)
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXBondToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXBondToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXBondToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXBondToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXBondToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXBondToken.status == status)
        if personal_info_address is not None:
            query = query.filter(IDXBondToken.personal_info_address == personal_info_address)
        if transferable is not None:
            query = query.filter(IDXBondToken.transferable == transferable)
        if is_offering is not None:
            query = query.filter(IDXBondToken.is_offering == is_offering)
        if transfer_approval_required is not None:
            query = query.filter(IDXBondToken.transfer_approval_required == transfer_approval_required)
        if is_redeemed is not None:
            query = query.filter(IDXBondToken.is_redeemed == is_redeemed)
        count = query.count()

        sort_attr = getattr(IDXBondToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXBondToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXBondToken] = query.all()

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "address_list": [_token.token_address for _token in _token_list]
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "personal_info_address": req.get_param("personal_info_address"),
            "transferable": req.get_param_as_bool("transferable"),
            "is_offering": req.get_param_as_bool("is_offering"),
            "transfer_approval_required": req.get_param_as_bool("transfer_approval_required"),
            "is_redeemed": req.get_param_as_bool("is_redeemed"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "personal_info_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_offering": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transfer_approval_required": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_redeemed": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "token_address",
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "personal_info_address",
                    "transferable",
                    "is_offering",
                    "transfer_approval_required",
                    "is_redeemed"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
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


class ShareTokens(BaseResource):
    """
    Endpoint: /v3/Token/Share
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = ShareTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        personal_info_address: Optional[str] = request_json.get("personal_info_address")
        transferable: Optional[bool] = request_json.get("transferable", None)
        is_offering: Optional[bool] = request_json.get("is_offering", None)
        transfer_approval_required: Optional[bool] = request_json.get("transfer_approval_required", None)
        is_canceled: Optional[bool] = request_json.get("is_canceled", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXShareToken).\
            join(Listing, Listing.token_address == IDXShareToken.token_address).\
            filter(Listing.is_public == True)
        if len(request_json["address_list"]) > 0:
            query = query.filter(IDXShareToken.token_address.in_(request_json["address_list"]))
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXShareToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXShareToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXShareToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXShareToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXShareToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXShareToken.status == status)
        if personal_info_address is not None:
            query = query.filter(IDXShareToken.personal_info_address == personal_info_address)
        if transferable is not None:
            query = query.filter(IDXShareToken.transferable == transferable)
        if is_offering is not None:
            query = query.filter(IDXShareToken.is_offering == is_offering)
        if transfer_approval_required is not None:
            query = query.filter(IDXShareToken.transfer_approval_required == transfer_approval_required)
        if is_canceled is not None:
            query = query.filter(IDXShareToken.is_canceled == is_canceled)
        count = query.count()

        sort_attr = getattr(IDXShareToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXShareToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXShareToken] = query.all()
        tokens = []

        for _token in _token_list:
            tokens.append(ShareToken.from_model(_token).__dict__)

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "tokens": tokens
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "address_list": req.get_param_as_list("address_list", default=[]),
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "personal_info_address": req.get_param("personal_info_address"),
            "transferable": req.get_param_as_bool("transferable"),
            "is_offering": req.get_param_as_bool("is_offering"),
            "transfer_approval_required": req.get_param_as_bool("transfer_approval_required"),
            "is_canceled": req.get_param_as_bool("is_canceled"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False,
                "nullable": False,
            },
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "personal_info_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_offering": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transfer_approval_required": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_canceled": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "token_address",
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "personal_info_address",
                    "transferable",
                    "is_offering",
                    "transfer_approval_required",
                    "is_canceled"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for address in request_json["address_list"]:
            try:
                to_checksum_address(address)
            except ValueError:
                description = f"invalid token_address: {address}"
                raise InvalidParameterError(description=description)

        return validator.document


class ShareTokenAddresses(BaseResource):
    """
    Endpoint: /v3/Token/Share/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = ShareTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        personal_info_address: Optional[str] = request_json.get("personal_info_address", None)
        transferable: Optional[bool] = request_json.get("transferable", None)
        is_offering: Optional[bool] = request_json.get("is_offering", None)
        transfer_approval_required: Optional[bool] = request_json.get("transfer_approval_required", None)
        is_canceled: Optional[bool] = request_json.get("is_canceled", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXShareToken).\
            join(Listing, Listing.token_address == IDXShareToken.token_address).\
            filter(Listing.is_public == True)
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXShareToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXShareToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXShareToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXShareToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXShareToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXShareToken.status == status)
        if personal_info_address is not None:
            query = query.filter(IDXShareToken.personal_info_address == personal_info_address)
        if transferable is not None:
            query = query.filter(IDXShareToken.transferable == transferable)
        if is_offering is not None:
            query = query.filter(IDXShareToken.is_offering == is_offering)
        if transfer_approval_required is not None:
            query = query.filter(IDXShareToken.transfer_approval_required == transfer_approval_required)
        if is_canceled is not None:
            query = query.filter(IDXShareToken.is_canceled == is_canceled)
        count = query.count()

        sort_attr = getattr(IDXShareToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXShareToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXShareToken] = query.all()

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "address_list": [_token.token_address for _token in _token_list]
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "personal_info_address": req.get_param("personal_info_address"),
            "transferable": req.get_param_as_bool("transferable"),
            "is_offering": req.get_param_as_bool("is_offering"),
            "transfer_approval_required": req.get_param_as_bool("transfer_approval_required"),
            "is_canceled": req.get_param_as_bool("is_canceled"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "personal_info_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_offering": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transfer_approval_required": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "is_canceled": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "token_address",
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "personal_info_address",
                    "transferable",
                    "is_offering",
                    "transfer_approval_required",
                    "is_canceled"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
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


class MembershipTokens(BaseResource):
    """
    Endpoint: /v3/Token/Membership
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = MembershipTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        transferable: Optional[bool] = request_json.get("transferable", None)
        initial_offering_status: Optional[bool] = request_json.get("initial_offering_status", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXMembershipToken).\
            join(Listing, Listing.token_address == IDXMembershipToken.token_address).\
            filter(Listing.is_public == True)
        if len(request_json["address_list"]) > 0:
            query = query.filter(IDXMembershipToken.token_address.in_(request_json["address_list"]))
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXMembershipToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXMembershipToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXMembershipToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXMembershipToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXMembershipToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXMembershipToken.status == status)
        if transferable is not None:
            query = query.filter(IDXMembershipToken.transferable == transferable)
        if initial_offering_status is not None:
            query = query.filter(IDXMembershipToken.initial_offering_status == initial_offering_status)
        count = query.count()

        sort_attr = getattr(IDXMembershipToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXMembershipToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXMembershipToken] = query.all()
        tokens = []

        for _token in _token_list:
            tokens.append(MembershipToken.from_model(_token).__dict__)

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "tokens": tokens
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "address_list": req.get_param_as_list("address_list", default=[]),
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "transferable": req.get_param_as_bool("transferable"),
            "initial_offering_status": req.get_param_as_bool("initial_offering_status"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False,
                "nullable": False,
            },
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "initial_offering_status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "transferable",
                    "initial_offering_status"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for address in request_json["address_list"]:
            try:
                to_checksum_address(address)
            except ValueError:
                description = f"invalid token_address: {address}"
                raise InvalidParameterError(description=description)

        return validator.document


class MembershipTokenAddresses(BaseResource):
    """
    Endpoint: /v3/Token/Membership/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = MembershipTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        transferable: Optional[bool] = request_json.get("transferable", None)
        initial_offering_status: Optional[bool] = request_json.get("initial_offering_status", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXMembershipToken).\
            join(Listing, Listing.token_address == IDXMembershipToken.token_address).\
            filter(Listing.is_public == True)
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXMembershipToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXMembershipToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXMembershipToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXMembershipToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXMembershipToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXMembershipToken.status == status)
        if transferable is not None:
            query = query.filter(IDXMembershipToken.transferable == transferable)
        if initial_offering_status is not None:
            query = query.filter(IDXMembershipToken.initial_offering_status == initial_offering_status)
        count = query.count()

        sort_attr = getattr(IDXMembershipToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXMembershipToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXMembershipToken] = query.all()

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "address_list": [_token.token_address for _token in _token_list]
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "transferable": req.get_param_as_bool("transferable"),
            "initial_offering_status": req.get_param_as_bool("initial_offering_status"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "initial_offering_status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "transferable",
                    "initial_offering_status"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
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


class CouponTokens(BaseResource):
    """
    Endpoint: /v3/Token/Coupon
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = CouponTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        transferable: Optional[bool] = request_json.get("transferable", None)
        initial_offering_status: Optional[bool] = request_json.get("initial_offering_status", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXCouponToken).\
            join(Listing, Listing.token_address == IDXCouponToken.token_address).\
            filter(Listing.is_public == True)
        if len(request_json["address_list"]) > 0:
            query = query.filter(IDXCouponToken.token_address.in_(request_json["address_list"]))
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXCouponToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXCouponToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXCouponToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXCouponToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXCouponToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXCouponToken.status == status)
        if transferable is not None:
            query = query.filter(IDXCouponToken.transferable == transferable)
        if initial_offering_status is not None:
            query = query.filter(IDXCouponToken.initial_offering_status == initial_offering_status)
        count = query.count()

        sort_attr = getattr(IDXCouponToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXCouponToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXCouponToken] = query.all()
        tokens = []

        for _token in _token_list:
            tokens.append(CouponToken.from_model(_token).__dict__)

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "tokens": tokens
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "address_list": req.get_param_as_list("address_list", default=[]),
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "transferable": req.get_param_as_bool("transferable"),
            "initial_offering_status": req.get_param_as_bool("initial_offering_status"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "address_list": {
                "type": "list",
                "schema": {"type": "string"},
                "required": False,
                "nullable": False,
            },
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "initial_offering_status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "transferable",
                    "initial_offering_status"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for address in request_json["address_list"]:
            try:
                to_checksum_address(address)
            except ValueError:
                description = f"invalid token_address: {address}"
                raise InvalidParameterError(description=description)

        return validator.document


class CouponTokenAddresses(BaseResource):
    """
    Endpoint: /v3/Token/Coupon/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = CouponTokens.validate(req)

        owner_address: Optional[str] = request_json.get("owner_address", None)
        name: Optional[str] = request_json.get("name", None)
        symbol: Optional[str] = request_json.get("symbol", None)
        company_name: Optional[str] = request_json.get("company_name", None)
        tradable_exchange: Optional[str] = request_json.get("tradable_exchange", None)
        status: Optional[bool] = request_json.get("status", None)
        transferable: Optional[bool] = request_json.get("transferable", None)
        initial_offering_status: Optional[bool] = request_json.get("initial_offering_status", None)

        sort_item = "created" if request_json["sort_item"] is None else request_json["sort_item"]
        sort_order = 0 if request_json["sort_order"] is None else request_json["sort_order"]  # default: asc
        offset = request_json["offset"]
        limit = request_json["limit"]

        # 取扱トークンリストを取得
        # 公開属性によるフィルタリングを行うためJOIN
        query = session.query(IDXCouponToken).\
            join(Listing, Listing.token_address == IDXCouponToken.token_address).\
            filter(Listing.is_public == True)
        total = query.count()

        # Search Filter
        if owner_address is not None:
            query = query.filter(IDXCouponToken.owner_address == owner_address)
        if name is not None:
            query = query.filter(IDXCouponToken.name.contains(name))
        if symbol is not None:
            query = query.filter(IDXCouponToken.symbol.contains(symbol))
        if company_name is not None:
            query = query.filter(IDXCouponToken.company_name.contains(company_name))
        if tradable_exchange is not None:
            query = query.filter(IDXCouponToken.tradable_exchange == tradable_exchange)
        if status is not None:
            query = query.filter(IDXCouponToken.status == status)
        if transferable is not None:
            query = query.filter(IDXCouponToken.transferable == transferable)
        if initial_offering_status is not None:
            query = query.filter(IDXCouponToken.initial_offering_status == initial_offering_status)
        count = query.count()

        sort_attr = getattr(IDXCouponToken, sort_item, None)

        if sort_order == 0:  # ASC
            query = query.order_by(sort_attr)
        else:  # DESC
            query = query.order_by(desc(sort_attr))
        if sort_item != "created":
            # NOTE: Set secondary sort for consistent results
            query = query.order_by(IDXCouponToken.created)

        # Pagination
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)

        _token_list: list[IDXCouponToken] = query.all()

        data = {
            "result_set": {
                "count": count,
                "offset": offset,
                "limit": limit,
                "total": total
            },
            "address_list": [_token.token_address for _token in _token_list]
        }

        self.on_success(res, data)

    @staticmethod
    def validate(req: Request):
        request_json = {
            "owner_address": req.get_param("owner_address"),
            "name": req.get_param("name"),
            "symbol": req.get_param("symbol"),
            "company_name": req.get_param("company_name"),
            "tradable_exchange": req.get_param("tradable_exchange"),
            "status": req.get_param_as_bool("status"),
            "transferable": req.get_param_as_bool("transferable"),
            "initial_offering_status": req.get_param_as_bool("initial_offering_status"),

            "sort_item": req.get_param("sort_item"),
            "sort_order": req.get_param("sort_order"),
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit"),
        }

        validator = Validator({
            "owner_address": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "symbol": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "company_name": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "tradable_exchange": {
                "type": "string",
                "required": False,
                "nullable": True
            },
            "status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "transferable": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "initial_offering_status": {
                "type": "boolean",
                "required": False,
                "nullable": True
            },
            "sort_item": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": [
                    "owner_address",
                    "name",
                    "symbol",
                    "company_name",
                    "tradable_exchange",
                    "status",
                    "transferable",
                    "initial_offering_status"
                ]
            },
            # NOTE: 0:asc, 1:desc
            "sort_order": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "max": 1,
                "required": False,
                "nullable": True,
            },
            "offset": {
                "type": "integer",
                "coerce": int,
                "min": 0,
                "required": False,
                "nullable": True,
            },
            "limit": {
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
