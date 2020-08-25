# -*- coding: utf-8 -*-
from cerberus import Validator

from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, DataNotExistsError, AppError
from app.model import Listing, ExecutableContract

LOG = log.get_logger()


# ------------------------------
# [管理]取扱トークン登録/一覧取得
# ------------------------------
class Tokens(BaseResource):
    """
    Endpoint: /v2/Admin/Tokens
      - GET: 取扱トークン一覧取得
      - POST: 取扱トークン登録
    """

    ########################################
    # GET
    ########################################
    def on_get(self, req, res):
        LOG.info("v2.token.Tokens(GET)")

        session = req.context["session"]

        res_body = []

        listed_tokens = session.query(Listing).all()
        for token in listed_tokens:
            item = token.json()
            res_body.append(item)

        # idの降順にソート
        res_body.sort(key=lambda x: x["id"], reverse=True)

        self.on_success(res, res_body)

    ########################################
    # POST
    ########################################
    def on_post(self, req, res):
        LOG.info("v2.token.Tokens(POST)")

        session = req.context["session"]

        # 入力値チェック
        request_json = self.validate(req)
        contract_address = request_json["contract_address"]

        # 既存レコードの存在チェック
        _listing = session.query(Listing). \
            filter(Listing.token_address == contract_address). \
            first()
        if _listing is not None:
            raise InvalidParameterError("contract_address already exist")

        _executable_contract = session.query(ExecutableContract). \
            filter(ExecutableContract.contract_address == contract_address). \
            first()
        if _executable_contract is not None:
            raise InvalidParameterError("contract_address already exist")

        # 新規レコードの登録
        is_public = request_json["is_public"]
        max_holding_quantity = request_json["max_holding_quantity"] if "max_holding_quantity" in request_json else None
        max_sell_amount = request_json["max_sell_amount"] if "max_sell_amount" in request_json else None
        owner_address = request_json["owner_address"]

        listing = Listing()
        listing.token_address = contract_address
        listing.is_public = is_public
        listing.max_holding_quantity = max_holding_quantity
        listing.max_sell_amount = max_sell_amount
        listing.owner_address = owner_address
        session.add(listing)

        executable_contract = ExecutableContract()
        executable_contract.contract_address = contract_address
        session.add(executable_contract)

        session.commit()

        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "contract_address": {
                "type": "string",
                "required": True,
                "nullable": False
            },
            "is_public": {
                "type": "boolean",
                "required": True,
                "nullable": False
            },
            "max_holding_quantity": {
                "type": "integer",
                "required": False,
            },
            "max_sell_amount": {
                "type": "integer",
                "required": False,
            },
            "owner_address": {
                "type": "string",
                "required": True,
                "nullable": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        # contract_addressのフォーマットチェック
        try:
            if not Web3.isAddress(request_json["contract_address"]):
                raise InvalidParameterError("Invalid contract address")
        except Exception as err:
            LOG.warning(f"invalid contract address: {err}")
            raise InvalidParameterError("Invalid contract address")

        # owner_addressのフォーマットチェック
        try:
            if not Web3.isAddress(request_json["owner_address"]):
                raise InvalidParameterError("Invalid owner address")
        except Exception as err:
            LOG.warning(f"invalid owner address: {err}")
            raise InvalidParameterError("Invalid owner address")

        return request_json


# ------------------------------
# [管理]取扱トークン情報取得/更新
# ------------------------------
class Token(BaseResource):
    """
    Endpoint: /v2/Admin/Token/{contract_address}
      - GET: 取扱トークン情報取得（個別）
      - POST: 取扱トークン情報更新（個別）
      - DELETE: 取扱トークン情報削除（個別）
    """

    ########################################
    # GET
    ########################################
    def on_get(self, req, res, contract_address=None):
        LOG.info("v2.token.Token(GET)")

        session = req.context["session"]

        token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        res_body = token.json()

        self.on_success(res, res_body)

    ########################################
    # POST
    ########################################
    def on_post(self, req, res, contract_address=None):
        LOG.info("v2.token.Token(POST)")

        session = req.context["session"]

        # 入力値チェック
        request_json = self.validate(req)

        # contract_addressのフォーマットチェック
        try:
            if not Web3.isAddress(contract_address):
                raise InvalidParameterError("Invalid contract address")
        except Exception as err:
            LOG.warning(f"invalid contract address: {err}")
            raise InvalidParameterError("Invalid contract address")

        # 更新対象レコードを取得
        # 更新対象のレコードが存在しない場合は404エラーを返す
        token = session.query(Listing).filter(Listing.token_address == contract_address).first()
        if token is None:
            raise DataNotExistsError("Record does not exist")

        # レコードの更新
        is_public = request_json["is_public"] if "is_public" in request_json \
            else token.is_public
        max_holding_quantity = request_json["max_holding_quantity"] if "max_holding_quantity" in request_json \
            else token.max_holding_quantity
        max_sell_amount = request_json["max_sell_amount"] if "max_sell_amount" in request_json \
            else token.max_sell_amount
        owner_address = request_json["owner_address"] if "max_sell_amount" in request_json \
            else token.owner_address

        token.is_public = is_public
        token.max_holding_quantity = max_holding_quantity
        token.max_sell_amount = max_sell_amount
        token.owner_address = owner_address
        session.merge(token)
        session.commit()

        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "is_public": {
                "type": "boolean",
                "required": False,
            },
            "max_holding_quantity": {
                "type": "integer",
                "required": False,
            },
            "max_sell_amount": {
                "type": "integer",
                "required": False,
            },
            "owner_address": {
                "type": "string",
                "required": False
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        # owner_addressのフォーマットチェック
        if "owner_address" in request_json:
            try:
                if not Web3.isAddress(request_json["owner_address"]):
                    raise InvalidParameterError("Invalid owner address")
            except Exception as err:
                LOG.warning(f"invalid owner address: {err}")
                raise InvalidParameterError("Invalid owner address")

        return request_json

    ########################################
    # DELETE
    ########################################
    def on_delete(self, req, res, contract_address=None):
        LOG.info("v2.token.Token(DELETE)")

        session = req.context["session"]

        # contract_addressのフォーマットチェック
        try:
            if not Web3.isAddress(contract_address):
                raise InvalidParameterError("Invalid contract address")
        except Exception as err:
            LOG.warning(f"invalid contract address: {err}")
            raise InvalidParameterError("Invalid contract address")

        try:
            session.query(Listing).filter(Listing.token_address == contract_address).delete()
            session.query(ExecutableContract).filter(ExecutableContract.contract_address == contract_address).delete()
        except Exception as err:
            LOG.exception(f"Failed to delete the data: {err}")
            raise AppError()

        self.on_success(res)
