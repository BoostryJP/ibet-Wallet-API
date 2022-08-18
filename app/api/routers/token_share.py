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

from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    NotSupportedError, DataNotExistsError
)
from app import config
from app.model.blockchain import ShareToken
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Listing,
    IDXShareToken,
)

LOG = log.get_logger()


class ShareTokens(BaseResource):
    """
    Endpoint: /Token/Share
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
    Endpoint: /Token/Share/Addresses
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


class ShareTokenDetails(BaseResource):
    """
    Endpoint: /Token/Share/{contract_address}
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, **kwargs):
        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # 入力アドレスフォーマットチェック
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                description = 'invalid contract_address'
                raise InvalidParameterError(description=description)
        except:
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)

        session = req.context["session"]

        # 取扱トークン情報を取得
        # NOTE:非公開トークンも取扱対象とする
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address). \
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        token_address = to_checksum_address(contract_address)

        token_detail = self.get_token_detail(
            session=session,
            token_address=token_address,
            include_inactive_tokens=True
        )
        if token_detail is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        self.on_success(res, token_detail.__dict__)

    @staticmethod
    def get_token_detail(session,
                         token_address: str,
                         include_inactive_tokens: bool = False):
        """
        トークン詳細の取得

        :param session: DB Session
        :param token_address: トークンアドレス
        :param include_inactive_tokens: statusが無効のトークンを含めるかどうか
        :return: ShareToken
        """

        try:
            sharetoken = ShareToken.get(session=session, token_address=token_address)
            if not include_inactive_tokens and not sharetoken.status:
                return None
            return sharetoken
        except Exception as e:
            LOG.error(e)
            return None
