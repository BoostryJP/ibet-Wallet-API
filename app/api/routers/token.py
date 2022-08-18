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
import uuid
from typing import List
from cerberus import Validator
from sqlalchemy import (
    or_,
    desc,
    asc
)
from web3 import Web3
from eth_utils import to_checksum_address
from falcon import Request, Response
from sqlalchemy.orm import Session

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)
from app import config
from app.contracts import Contract
from app.utils.web3_utils import Web3Wrapper
from app.model.db import (
    Listing,
    IDXPosition,
    IDXTransfer,
    IDXTransferApproval,
    TokenHoldersList,
    TokenHolderBatchStatus,
    TokenHolder
)

LOG = log.get_logger()


class TokenStatus(BaseResource):
    """
    Endpoint: /Token/{contract_address}/Status
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_get(self, req, res, contract_address=None, **kwargs):
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


class TokenHolders(BaseResource):
    """
    Endpoint: /Token/{contract_address}/Holders
    """

    def on_get(self, req, res, contract_address=None, **kwargs):
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
        # add order_by id to bridge the difference between postgres and mysql
        holders = session.query(IDXPosition). \
            filter(IDXPosition.token_address == contract_address). \
            filter(or_(
                IDXPosition.balance > 0,
                IDXPosition.pending_transfer > 0,
                IDXPosition.exchange_balance > 0,
                IDXPosition.exchange_commitment > 0)). \
            order_by(desc(IDXPosition.id)) .\
            all()

        resp_body = []
        for holder in holders:
            resp_body.append({
                "token_address": holder.token_address,
                "account_address": holder.account_address,
                "amount": holder.balance,
                "pending_transfer": holder.pending_transfer,
                "exchange_balance": holder.exchange_balance,
                "exchange_commitment": holder.exchange_commitment
            })

        self.on_success(res, resp_body)


class TokenHoldersCount(BaseResource):
    """
    Endpoint: /Token/{contract_address}/Holders/Count
    """

    def on_get(self, req, res, contract_address=None, **kwargs):
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
        # add order_by id to bridge the difference between postgres and mysql
        _count = session.query(IDXPosition). \
            filter(IDXPosition.token_address == contract_address). \
            filter(or_(
                IDXPosition.balance > 0,
                IDXPosition.pending_transfer > 0,
                IDXPosition.exchange_balance > 0,
                IDXPosition.exchange_commitment > 0)). \
            order_by(desc(IDXPosition.id)).count()

        resp_body = {
            "count": _count
        }

        self.on_success(res, resp_body)


class TokenHoldersCollection(BaseResource):
    """
    Endpoint: /Token/{contract_address}/Holders/Collection
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3Wrapper()

    def on_post(self, req: Request, res: Response, *args, **kwargs):
        """Token holders collection"""
        session: Session = req.context["session"]

        # body部の入力値チェック
        request_json = self.validate(req)
        list_id = request_json["list_id"]
        block_number = request_json["block_number"]

        # contract_addressのフォーマットチェック
        contract_address = kwargs.get("contract_address", "")
        try:
            if not Web3.isAddress(contract_address):
                raise InvalidParameterError("Invalid contract address")
        except Exception as err:
            LOG.debug(f"invalid contract address: {err}")
            raise InvalidParameterError("Invalid contract address")

        # ブロックナンバーのチェック
        if block_number > self.web3.eth.block_number or block_number < 1:
            raise InvalidParameterError("Block number must be current or past one.")

        # 取扱トークンチェック
        # NOTE:非公開トークンも取扱対象とする
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # list_idの衝突チェック
        _same_list_id_record = session.query(TokenHoldersList). \
            filter(TokenHoldersList.list_id == list_id). \
            first()
        if _same_list_id_record is not None:
            raise InvalidParameterError("list_id must be unique.")

        _same_combi_record = session.query(TokenHoldersList). \
            filter(TokenHoldersList.token_address == contract_address). \
            filter(TokenHoldersList.block_number == block_number). \
            filter(TokenHoldersList.batch_status != TokenHolderBatchStatus.FAILED.value). \
            first()

        if _same_combi_record is not None:
            # 同じブロックナンバー・トークンアドレスのコレクションが、PENDINGかDONEで既に存在する場合、
            # そのlist_idとstatusを返却する。
            return self.on_success(res, {
                "list_id": _same_combi_record.list_id,
                "status": _same_combi_record.batch_status,
            })
        else:
            token_holder_list = TokenHoldersList()
            token_holder_list.list_id = list_id
            token_holder_list.batch_status = TokenHolderBatchStatus.PENDING.value
            token_holder_list.block_number = block_number
            token_holder_list.token_address = contract_address
            session.add(token_holder_list)
            session.commit()

            return self.on_success(res, {
                "list_id": token_holder_list.list_id,
                "status": token_holder_list.batch_status,
            })

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "list_id": {
                "type": "string",
                "required": True
            },
            "block_number": {
                "type": "integer",
                "required": True
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        # UUIDのフォーマットチェック
        try:
            if not uuid.UUID(request_json["list_id"]).version == 4:
                description = "list_id must be UUIDv4."
                raise InvalidParameterError(description=description)
        except:
            description = "list_id must be UUIDv4."
            raise InvalidParameterError(description=description)
        return request_json


class TokenHoldersCollectionId(BaseResource):
    """
    Endpoint: /Token/{contract_address}/Holders/Collection/{list_id}
    """

    def on_get(self, req: Request, res: Response, *args, **kwargs):
        """Token holders collection Id"""
        contract_address = kwargs.get("contract_address", "")
        list_id = kwargs.get("list_id", "")

        # 入力アドレスフォーマットチェック
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                description = 'invalid contract_address'
                raise InvalidParameterError(description=description)
        except:
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)

        # 入力IDフォーマットチェック
        try:
            if not uuid.UUID(list_id).version == 4:
                description = "list_id must be UUIDv4."
                raise InvalidParameterError(description=description)
        except:
            description = "list_id must be UUIDv4."
            raise InvalidParameterError(description=description)

        session: Session = req.context["session"]

        # 取扱トークンチェック
        # NOTE:非公開トークンも取扱対象とする
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # 既存レコードの存在チェック
        _same_list_id_record: TokenHoldersList = session.query(TokenHoldersList). \
            filter(TokenHoldersList.list_id == list_id). \
            first()

        if not _same_list_id_record:
            raise DataNotExistsError("list_id: %s" % list_id)
        if _same_list_id_record.token_address != contract_address:
            description = "list_id: %s is not collection for contract_address: %s" % (list_id, contract_address)
            raise InvalidParameterError(description=description)

        _token_holders: List[TokenHolder] = session.query(TokenHolder). \
            filter(TokenHolder.holder_list == _same_list_id_record.id). \
            order_by(asc(TokenHolder.account_address)).\
            all()
        token_holders = [_token_holder.json() for _token_holder in _token_holders]

        return self.on_success(res, {
            "status": _same_list_id_record.batch_status,
            "holders": token_holders
        })


class TransferHistory(BaseResource):
    """
    Endpoint: /Token/{contract_address}/TransferHistory
    """

    def on_get(self, req, res, contract_address=None, **kwargs):
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


class TransferApprovalHistory(BaseResource):
    """
    Endpoint: /Token/{contract_address}/TransferApprovalHistory
    """

    def on_get(self, req, res, contract_address=None, **kwargs):
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
