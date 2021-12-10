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
from sqlalchemy import or_
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    DataNotExistsError,
    NotSupportedError
)
from app import config
from app.contracts import Contract
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Listing,
    IDXPosition,
    IDXTransfer,
    IDXTransferApproval
)
from app.model.blockchain import (
    BondToken,
    ShareToken,
    MembershipToken,
    CouponToken
)

LOG = log.get_logger()


# ------------------------------
# [トークン管理]トークン取扱ステータス
# ------------------------------
class TokenStatus(BaseResource):
    """
    Endpoint: /v2/Token/{contract_address}/Status
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.token.TokenStatus')

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

        # 取扱トークンチェック
        listed_token = session.query(Listing).filter(Listing.token_address == contract_address).first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = Contract.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )

        token_template = token[1]
        try:
            # Token-Contractへの接続
            token_contract = Contract.get_contract(token_template, token_address)
            status = Contract.call_function(
                contract=token_contract,
                function_name="status",
                args=()
            )
            transferable = Contract.call_function(
                contract=token_contract,
                function_name="transferable",
                args=()
            )
        except Exception as e:
            LOG.error(e)
            raise DataNotExistsError('contract_address: %s' % contract_address)

        response_json = {
            'token_template': token_template,
            'status': status,
            'transferable': transferable
        }
        self.on_success(res, response_json)


# /Token/{contract_address}/Holders
class TokenHolders(BaseResource):
    """トークン保有者一覧"""

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.token.TokenHolders')

        session = req.context["session"]

        # Validation
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                description = 'invalid contract_address'
                raise InvalidParameterError(description=description)
        except:
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)

        # Check if the token exists in the list
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # Get token holders
        holders = session.query(IDXPosition). \
            filter(IDXPosition.token_address == contract_address). \
            filter(or_(IDXPosition.balance > 0, IDXPosition.pending_transfer > 0)). \
            all()

        resp_body = []
        for holder in holders:
            resp_body.append({
                "token_address": holder.token_address,
                "account_address": holder.account_address,
                "amount": holder.balance,
                "pending_transfer": holder.pending_transfer
            })

        self.on_success(res, resp_body)


# /Token/{contract_address}/TransferHistory
class TransferHistory(BaseResource):
    """トークン移転履歴"""

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.token.TransferHistory')

        session = req.context["session"]

        # 入力値チェック
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                description = 'invalid contract_address'
                raise InvalidParameterError(description=description)
        except:
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)

        # validation
        request_json = self.validate(req)

        # 取扱トークンチェック
        listed_token = session.query(Listing). \
            filter(Listing.token_address == contract_address). \
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # 移転履歴取得
        query = session.query(IDXTransfer). \
            filter(IDXTransfer.token_address == contract_address). \
            order_by(IDXTransfer.id)
        list_length = query.count()

        if request_json["offset"] is not None:
            query = query.offset(request_json['offset'])
        if request_json["limit"] is not None:
            query = query.limit(request_json['limit'])
        transfer_history = query.all()

        resp_data = []
        for transfer_event in transfer_history:
            resp_data.append(transfer_event.json())

        data = {
            "result_set": {
                "count": list_length,
                "offset": request_json['offset'],
                "limit": request_json['limit'],
                "total": list_length
            },
            "transfer_history": resp_data
        }
        self.on_success(res, data=data)

    @staticmethod
    def validate(req):
        request_json = {
            "offset": req.get_param("offset"),
            "limit": req.get_param("limit")
        }

        validator = Validator({
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


# /Token/{contract_address}/TransferApprovalHistory
class TransferApprovalHistory(BaseResource):
    """トークン移転承諾履歴"""

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info("v2.token.TransferApprovalHistory")
        db_session = req.context["session"]

        # Validation
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                raise InvalidParameterError("invalid contract_address")
        except:
            raise InvalidParameterError("invalid contract_address")

        request_json = self.validate(req)

        # Check that it is a listed token
        _listed_token = db_session.query(Listing). \
            filter(Listing.token_address == contract_address). \
            first()
        if _listed_token is None:
            raise DataNotExistsError(f"contract_address: {contract_address}")

        # Get transfer approval data
        query = db_session.query(IDXTransferApproval). \
            filter(IDXTransferApproval.token_address == contract_address). \
            order_by(
                IDXTransferApproval.exchange_address,
                IDXTransferApproval.application_id
            )
        list_length = query.count()

        # パラメータを設定
        if request_json["offset"] is not None:
            query = query.offset(request_json["offset"])
        if request_json["limit"] is not None:
            query = query.limit(request_json["limit"])
        transfer_approval_history = query.all()

        resp_data = []
        for transfer_approval_event in transfer_approval_history:
            resp_data.append(transfer_approval_event.json())
        data = {
            "result_set": {
                "count": list_length,
                "offset": request_json['offset'],
                "limit": request_json['limit'],
                "total": list_length
            },
            "transfer_approval_history": resp_data
        }
        self.on_success(res, data=data)

    @staticmethod
    def validate(req):
        request_json = {
            'offset': req.get_param('offset'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'offset': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [普通社債]公開中トークン一覧
# ------------------------------
class StraightBondTokens(BaseResource):
    """
    Endpoint: /v2/Token/StraightBond
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.StraightBondTokens')

        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = StraightBondTokens.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        for i in reversed(range(0, cursor)):  # NOTE:登録の新しい順になるようにする
            if count >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            token_detail = StraightBondTokenDetails.get_token_detail(
                session=session,
                token_id=i,
                token_address=token_address,
                token_template=token[1]
            )

            if token_detail is not None:
                token_list.append(token_detail)
                count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [普通社債]公開中トークン一覧（トークンアドレス）
# ------------------------------
class StraightBondTokenAddresses(BaseResource):
    """
    Endpoint: /v2/Token/StraightBond/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.StraightBondAddresses')

        session = req.context["session"]

        if config.BOND_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = self.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        for i in reversed(range(0, cursor)):  # NOTE:登録の新しい順になるようにする
            if count >= limit:
                break
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            if token[1] == 'IbetStraightBond':  # ibetStraightBond以外は処理をスキップ
                # トークンコントラクトへの接続
                token_contract = Contract.get_contract("IbetStraightBond", token_address)
                if Contract.call_function(token_contract, "isRedeemed", (), False) is False:  # 償還済みの場合は処理をスキップ
                    token_list.append({"id": i, "token_address": token_address})
                    count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [普通社債]トークン詳細
# ------------------------------
class StraightBondTokenDetails(BaseResource):
    """
    Endpoint: /v2/Token/StraightBond/{contract_address}
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, *args, **kwargs):
        LOG.info('v2.token.StraightBondTokenDetails')

        if config.BOND_TOKEN_ENABLED is False:
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

        # 取扱トークンチェック
        # NOTE:非公開トークンも取扱対象とする
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = Contract.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )

        token_detail = self.get_token_detail(
            session=session,
            token_address=token_address,
            token_template=token[1]
        )
        if token_detail is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        self.on_success(res, token_detail)

    @staticmethod
    def get_token_detail(session, token_address: str, token_template: str, token_id: int = None):
        """
        トークン詳細の取得

        :param session: DB Session
        :param token_address: トークンアドレス
        :param token_template: トークンテンプレート
        :param token_id: シーケンスID（任意）
        :return: BondToken(dict)
        """

        if token_template == 'IbetStraightBond':
            try:
                # トークンコントラクトへの接続
                token_contract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not Contract.call_function(token_contract, "status", (), True):
                    return None
                bondtoken = BondToken.get(session=session, token_address=token_address)
                bondtoken = bondtoken.__dict__
                if token_id is not None:
                    bondtoken['id'] = token_id
                return bondtoken
            except Exception as e:
                LOG.error(e)
                return None


# ------------------------------
# [株式]公開中トークン一覧
# ------------------------------
class ShareTokens(BaseResource):
    """
    Endpoint: /v2/Token/Share
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.ShareTokens')

        session = req.context["session"]

        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = ShareTokens.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if count >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )

            token_detail = ShareTokenDetails.get_token_detail(
                session=session,
                token_address=token_address,
                token_template=token[1],
            )
            if token_detail is not None:
                token_detail["id"] = i
                token_list.append(token_detail)
                count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [株式]公開中トークン一覧（トークンアドレス）
# ------------------------------
class ShareTokenAddresses(BaseResource):
    """
    Endpoint: /v2/Token/Share/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.ShareTokenAddresses')

        session = req.context["session"]

        if config.SHARE_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = self.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if count >= limit:
                break
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            if token[1] == 'IbetShare':  # ibetShare以外は処理をスキップ
                # Token-Contractへの接続
                token_contract = Contract.get_contract("IbetShare", token_address)
                if Contract.call_function(token_contract, "status", (), True):  # 取扱停止の場合は処理をスキップ
                    token_list.append({"id": i, "token_address": token_address})
                    count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [株式]トークン詳細
# ------------------------------
class ShareTokenDetails(BaseResource):
    """
    Endpoint: /v2/Token/Share/{contract_address}
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.token.ShareTokenDetails')

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

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = Contract.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )

        token_detail = self.get_token_detail(
            session=session,
            token_address=token_address,
            token_template=token[1]
        )
        if token_detail is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        self.on_success(res, token_detail)

    @staticmethod
    def get_token_detail(session, token_address: str, token_template: str, token_id: int = None):
        """
        トークン詳細の取得

        :param session: DB Session
        :param token_address: トークンアドレス
        :param token_template: トークンテンプレート
        :param token_id: シーケンスID（任意）
        :return: ShareToken(dict)
        """

        if token_template == 'IbetShare':
            try:
                # Token-Contractへの接続
                token_contract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not Contract.call_function(token_contract, "status", (), True):
                    return None
                sharetoken = ShareToken.get(session=session, token_address=token_address)
                sharetoken = sharetoken.__dict__
                if token_id is not None:
                    sharetoken['id'] = token_id
                return sharetoken
            except Exception as e:
                LOG.error(e)
                return None


# ------------------------------
# [会員権]公開中トークン一覧
# ------------------------------
class MembershipTokens(BaseResource):
    """
    Endpoint: /v2/Token/Membership
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.MembershipTokens')

        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = MembershipTokens.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if count >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )

            token_detail = MembershipTokenDetails.get_token_detail(
                session=session,
                token_id=i,
                token_address=token[0],
                token_template=token[1]
            )
            if token_detail is not None:
                token_list.append(token_detail)
                count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [会員権]公開中トークン一覧（トークンアドレス）
# ------------------------------
class MembershipTokenAddresses(BaseResource):
    """
    Endpoint: /v2/Token/Membership/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.MembershipTokenAddresses')

        session = req.context["session"]

        if config.MEMBERSHIP_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = MembershipTokens.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        for i in reversed(range(0, cursor)):
            if count >= limit:
                break
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            if token[1] == 'IbetMembership':  # ibetMembership以外は処理をスキップ
                # Token-Contractへの接続
                token_contract = Contract.get_contract("IbetMembership", token_address)
                if Contract.call_function(token_contract, "status", (), True):  # 取扱停止の場合は処理をスキップ
                    token_list.append({"id": i, "token_address": token_address})
                    count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [会員権]トークン詳細
# ------------------------------
class MembershipTokenDetails(BaseResource):
    """
    Endpoint: /v2/Token/Membership/{contract_address}
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.token.MembershipTokenDetails')

        if config.MEMBERSHIP_TOKEN_ENABLED is False:
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

        # 取扱トークンチェック
        # NOTE:非公開トークンも取扱対象とする
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = Contract.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )

        token_detail = self.get_token_detail(
            session=session,
            token_address=token_address,
            token_template=token[1],
        )
        if token_detail is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        self.on_success(res, token_detail)

    @staticmethod
    def get_token_detail(session, token_address: str, token_template: str, token_id: int = None):
        """
        トークン詳細の取得

        :param session: DB Session
        :param token_address: トークンアドレス
        :param token_template: トークンテンプレート
        :param token_id: シーケンスID（任意）
        :return: MembershipToken(dict)
        """

        if token_template == 'IbetMembership':
            try:
                # Token-Contractへの接続
                token_contract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not Contract.call_function(token_contract, "status", (), True):
                    return None
                membershiptoken = MembershipToken.get(session=session, token_address=token_address)
                membershiptoken = membershiptoken.__dict__
                if token_id is not None:
                    membershiptoken['id'] = token_id
                return membershiptoken
            except Exception as e:
                LOG.error(e)
                return None


# ------------------------------
# [クーポン]公開中トークン一覧
# ------------------------------
class CouponTokens(BaseResource):
    """
    Endpoint: /v2/Token/Coupon
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.CouponTokens')

        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = CouponTokens.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError(
                "cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if count >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )

            token_detail = CouponTokenDetails.get_token_detail(
                session=session,
                token_id=i,
                token_address=token_address,
                token_template=token[1],
            )
            if token_detail is not None:
                token_list.append(token_detail)
                count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [クーポン]公開中トークン一覧（トークンアドレス）
# ------------------------------
class CouponTokenAddresses(BaseResource):
    """
    Endpoint: /v2/Token/Coupon/Address
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.token.CouponTokenAddresses')

        session = req.context["session"]

        if config.COUPON_TOKEN_ENABLED is False:
            raise NotSupportedError(method='GET', url=req.path)

        # Validation
        request_json = CouponTokens.validate(req)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).\
            filter(Listing.is_public == True).\
            order_by(Listing.id).\
            all()
        list_length = len(available_tokens)

        if request_json['cursor'] is not None and request_json['cursor'] > list_length:
            raise InvalidParameterError(
                "cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        token_list = []
        count = 0
        for i in reversed(range(0, cursor)):
            if count >= limit:
                break
            token_address = to_checksum_address(available_tokens[i].token_address)
            token = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            if token[1] == 'IbetCoupon':  # ibetCoupon以外は処理をスキップ
                # Token-Contractへの接続
                token_contract = Contract.get_contract("IbetCoupon", token_address)
                if Contract.call_function(token_contract, "status", (), True):  # 取扱停止の場合は処理をスキップ
                    token_list.append({"id": i, "token_address": token_address})
                    count += 1

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'min': 0,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# [クーポン]トークン詳細
# ------------------------------
class CouponTokenDetails(BaseResource):
    """
    Endpoint: /v2/Token/Coupon/{contract_address}
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.token.CouponTokenDetails')

        if config.COUPON_TOKEN_ENABLED is False:
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

        # 取扱トークンチェック
        # NOTE:非公開トークンも取扱対象とする
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = Contract.call_function(
            contract=list_contract,
            function_name="getTokenByAddress",
            args=(token_address,),
            default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
        )

        token_detail = self.get_token_detail(
            session=session,
            token_address=token_address,
            token_template=token[1],
        )
        if token_detail is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        self.on_success(res, token_detail)

    @staticmethod
    def get_token_detail(session, token_address: str, token_template: str, token_id: int = None):
        """
        トークン詳細の取得

        :param session: DB Session
        :param token_address: トークンアドレス
        :param token_template: トークンテンプレート
        :param token_id: シーケンスID（任意）
        :return: CouponToken(dict)
        """

        if token_template == 'IbetCoupon':
            try:
                # Token-Contractへの接続
                token_contract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not Contract.call_function(token_contract, "status", (), True):
                    return None
                coupontoken = CouponToken.get(session=session, token_address=token_address)
                coupontoken = coupontoken.__dict__
                if token_id is not None:
                    coupontoken['id'] = token_id
                return coupontoken
            except Exception as e:
                LOG.error(e)
                return None
