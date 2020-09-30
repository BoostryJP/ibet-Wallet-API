# -*- coding: utf-8 -*-
from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, DataNotExistsError
from app import config
from app.contracts import Contract
from app.model import Listing, BondToken, ShareToken, MembershipToken, CouponToken, Position, Transfer

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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res, contract_address=None):
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
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = ListContract.functions.getTokenByAddress(token_address).call()

        token_template = token[1]
        try:
            # Token-Contractへの接続
            TokenContract = Contract.get_contract(token_template, token_address)
            status = TokenContract.functions.status().call()
        except Exception as e:
            LOG.error(e)
            raise DataNotExistsError('contract_address: %s' % contract_address)

        response_json = {
            'status': status
        }
        self.on_success(res, response_json)


# ------------------------------
# [トークン管理]トークン保有者一覧
# ------------------------------
class TokenHolders(BaseResource):
    """
    Endpoint: /v2/Token/{contract_address}/Holders
    """

    def on_get(self, req, res, contract_address=None):
        LOG.info('v2.token.TokenHolders')

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

        # 取扱トークンチェック
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # 保有者情報取得
        holders = session.query(Position). \
            filter(Position.token_address == contract_address). \
            filter(Position.balance > 0). \
            all()

        resp_body = []
        for holder in holders:
            resp_body.append({
                "token_address": holder.token_address,
                "account_address": holder.account_address,
                "amount": holder.balance
            })

        self.on_success(res, resp_body)


# ------------------------------
# [トークン管理]トークン移転履歴
# ------------------------------
class TransferHistory(BaseResource):
    """
    Endpoint: /v2/Token/{contract_address}/TransferHistory
    """

    def on_get(self, req, res, contract_address=None):
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

        # 取扱トークンチェック
        listed_token = session.query(Listing). \
            filter(Listing.token_address == contract_address). \
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # 移転履歴取得
        transfer_history = session.query(Transfer). \
            filter(Transfer.token_address == contract_address). \
            order_by(Transfer.id). \
            all()

        resp_body = []
        for transfer_event in transfer_history:
            resp_body.append(transfer_event.json())

        self.on_success(res, resp_body)


# ------------------------------
# [普通社債]公開中トークン一覧
# ------------------------------
class StraightBondTokens(BaseResource):
    """
    Endpoint: /v2/Token/StraightBond
    """

    def __init__(self):
        super().__init__()
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.StraightBondTokens')

        session = req.context["session"]

        # Validation
        request_json = StraightBondTokens.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.StraightBondAddresses')

        session = req.context["session"]

        # Validation
        request_json = self.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()
            if token[1] == 'IbetStraightBond':  # ibetStraightBond以外は処理をスキップ
                # トークンコントラクトへの接続
                TokenContract = Contract.get_contract("IbetStraightBond", token_address)
                if TokenContract.functions.isRedeemed().call() is False:  # 償還済みの場合は処理をスキップ
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res, contract_address=None):
        LOG.info('v2.token.StraightBondTokenDetails')

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
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            filter(Listing.is_public == True).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = ListContract.functions.getTokenByAddress(token_address).call()

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
                TokenContract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not TokenContract.functions.status().call():
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.ShareTokens')

        session = req.context["session"]

        # Validation
        request_json = ShareTokens.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.ShareTokenAddresses')

        session = req.context["session"]

        # Validation
        request_json = self.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()
            if token[1] == 'IbetShare':  # ibetShare以外は処理をスキップ
                # Token-Contractへの接続
                TokenContract = Contract.get_contract("IbetShare", token_address)
                if TokenContract.functions.status().call():  # 取扱停止の場合は処理をスキップ
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res, contract_address=None):
        LOG.info('v2.token.ShareTokenDetails')

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
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address). \
            filter(Listing.is_public == True). \
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = ListContract.functions.getTokenByAddress(token_address).call()

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
                TokenContract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not TokenContract.functions.status().call():
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.MembershipTokens')

        session = req.context["session"]

        # Validation
        request_json = MembershipTokens.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions. \
                getTokenByAddress(token_address).call()

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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.MembershipTokenAddresses')

        session = req.context["session"]

        # Validation
        request_json = MembershipTokens.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()
            if token[1] == 'IbetMembership':  # ibetMembership以外は処理をスキップ
                # Token-Contractへの接続
                TokenContract = Contract.get_contract("IbetMembership", token_address)
                if TokenContract.functions.status().call():  # 取扱停止の場合は処理をスキップ
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res, contract_address=None):
        LOG.info('v2.token.MembershipTokenDetails')

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
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            filter(Listing.is_public == True).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = ListContract.functions.getTokenByAddress(token_address).call()

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
                TokenContract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not TokenContract.functions.status().call():
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.CouponTokens')

        session = req.context["session"]

        # Validation
        request_json = CouponTokens.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()

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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res):
        LOG.info('v2.token.CouponTokenAddresses')

        session = req.context["session"]

        # Validation
        request_json = CouponTokens.validate(req)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

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
            token = ListContract.functions.getTokenByAddress(token_address).call()
            if token[1] == 'IbetCoupon':  # ibetCoupon以外は処理をスキップ
                # Token-Contractへの接続
                TokenContract = Contract.get_contract("IbetCoupon", token_address)
                if TokenContract.functions.status().call():  # 取扱停止の場合は処理をスキップ
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
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    def on_get(self, req, res, contract_address=None):
        LOG.info('v2.token.CouponTokenDetails')

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
        listed_token = session.query(Listing).\
            filter(Listing.token_address == contract_address).\
            filter(Listing.is_public == True).\
            first()
        if listed_token is None:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # TokenList-Contractからトークンの情報を取得する
        token_address = to_checksum_address(contract_address)
        token = ListContract.functions.getTokenByAddress(token_address).call()

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
                TokenContract = Contract.get_contract(token_template, token_address)
                # 取扱停止銘柄はリストに返さない
                if not TokenContract.functions.status().call():
                    return None
                coupontoken = CouponToken.get(session=session, token_address=token_address)
                coupontoken = coupontoken.__dict__
                if token_id is not None:
                    coupontoken['id'] = token_id
                return coupontoken
            except Exception as e:
                LOG.error(e)
                return None
