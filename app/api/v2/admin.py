"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed onan "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from cerberus import Validator

from web3 import Web3

from app import log
from app import config
from app.api.common import BaseResource
from app.contracts import Contract
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

        # token情報をTokenListコントラクトから取得
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)
            
        token = ListContract.functions.getTokenByAddress(
            contract_address).call()
        # contract_addressの有効性チェック
        if token[1] is None or token[1] not in self.available_token_template():
            raise InvalidParameterError("contract_address is invalid token address")

        owner_address = token[2]
        
        # 新規レコードの登録
        is_public = request_json["is_public"]
        max_holding_quantity = request_json["max_holding_quantity"] if "max_holding_quantity" in request_json else None
        max_sell_amount = request_json["max_sell_amount"] if "max_sell_amount" in request_json else None

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
                "min": 0
            },
            "max_sell_amount": {
                "type": "integer",
                "required": False,
                "min": 0
            },
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

        return request_json

    @staticmethod
    def available_token_template():
        """
        利用可能なtoken_templateをlistで返却

        :return: 利用可能なtoken_templateリスト
        """
        available_token_template_list = []
        if config.BOND_TOKEN_ENABLED:
            available_token_template_list.append("IbetStraightBond")
        if config.SHARE_TOKEN_ENABLED:
            available_token_template_list.append("IbetShare")
        if config.MEMBERSHIP_TOKEN_ENABLED:
            available_token_template_list.append("IbetMembership")
        if config.COUPON_TOKEN_ENABLED:
            available_token_template_list.append("IbetCoupon")
        return available_token_template_list


# ------------------------------
# [管理]取扱トークン種別
# ------------------------------
class TokenType(BaseResource):
    """
    Endpoint: /v2/Admin/Tokens/Type
      - GET: 取扱トークン種別
    """

    ########################################
    # GET
    ########################################
    def on_get(self, req, res):
        LOG.info("v2.token.TokenType")

        res_body = {
            "IbetStraightBond": config.BOND_TOKEN_ENABLED,
            "IbetShare": config.SHARE_TOKEN_ENABLED,
            "IbetMembership": config.MEMBERSHIP_TOKEN_ENABLED,
            "IbetCoupon": config.COUPON_TOKEN_ENABLED
        }

        self.on_success(res, res_body)


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

        if token is not None:
            res_body = token.json()
        else:
            raise DataNotExistsError()

        self.on_success(res, res_body)

    ########################################
    # POST
    ########################################
    def on_post(self, req, res, contract_address=None):
        LOG.info("v2.token.Token(POST)")

        session = req.context["session"]

        # 入力値チェック
        request_json = self.validate(req)

        # 更新対象レコードを取得
        # 更新対象のレコードが存在しない場合は404エラーを返す
        token = session.query(Listing).filter(Listing.token_address == contract_address).first()
        if token is None:
            raise DataNotExistsError()

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
                "min": 0
            },
            "max_sell_amount": {
                "type": "integer",
                "required": False,
                "min": 0
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

        try:
            session.query(Listing).filter(Listing.token_address == contract_address).delete()
            session.query(ExecutableContract).filter(ExecutableContract.contract_address == contract_address).delete()
        except Exception as err:
            LOG.exception(f"Failed to delete the data: {err}")
            raise AppError()

        self.on_success(res)
