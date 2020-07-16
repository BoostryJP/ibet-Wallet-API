# -*- coding: utf-8 -*-
from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address
from rlp import decode
from hexbytes import HexBytes

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError, SuspendedTokenError
from app import config
from app.model import ExecutableContract, Listing, PrivateListing
from app.contracts import Contract

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# nonce取得
# ------------------------------
class GetTransactionCount(BaseResource):
    """
    Handle for endpoint: /Eth/TransactionCount/{eth_address}
    """

    def on_get(self, req, res, eth_address=None):
        LOG.info('v2.eth.GetTransactionCount')

        try:
            eth_address = to_checksum_address(eth_address)
        except ValueError:
            raise InvalidParameterError

        nonce = web3.eth.getTransactionCount(to_checksum_address(eth_address))
        gasprice = web3.eth.gasPrice
        chainid = config.WEB3_CHAINID

        eth_info = {'nonce': nonce, 'gasprice': gasprice, 'chainid': chainid}
        self.on_success(res, eth_info)


# ------------------------------
# sendRawTransaction
# ------------------------------
class SendRawTransaction(BaseResource):
    """
    Handle for endpoint: /Eth/SendRawTransaction
    """

    def on_post(self, req, res):
        LOG.info('v2.eth.SendRawTransaction')

        session = req.context["session"]

        request_json = SendRawTransaction.validate(req)
        raw_tx_hex_list = request_json['raw_tx_hex_list']

        # トークン取扱状態チェック
        # トランザクション送信前にトークンの取扱状態をチェックする
        for raw_tx_hex in raw_tx_hex_list:
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address('0x' + raw_tx[3].hex())
            except Exception as err:
                LOG.info(f"RLP decoding failed: {err}")
                continue

            listed_token = session.query(Listing). \
                filter(Listing.token_address == to_contract_address). \
                first()
            private_listed_token = session.query(PrivateListing).\
                filter(PrivateListing.token_address == to_contract_address).\
                first()
            if listed_token is not None or private_listed_token is not None:
                TokenContract = Contract.get_contract("IbetStandardTokenInterface", to_contract_address)
                try:
                    if TokenContract.functions.status().call() is False:
                        raise SuspendedTokenError("Token is currently suspended")
                except Exception as err:
                    LOG.exception(f"{err}")

        # トランザクション送信
        result = []
        for i, raw_tx_hex in enumerate(raw_tx_hex_list):
            # 実行コントラクトのアドレスを取得
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address('0x' + raw_tx[3].hex())
                LOG.info(raw_tx)
            except Exception as err:
                result.append({'id': i + 1, 'status': 0})
                LOG.error(f"RLP decoding failed: {err}")
                continue

            # 実行可能コントラクトであることをチェック
            executable_contract = session.query(ExecutableContract). \
                filter(to_contract_address == ExecutableContract.contract_address). \
                first()
            if executable_contract is None:
                result.append({'id': i + 1, 'status': 0})
                LOG.error('Not executable')
                continue

            # ブロックチェーンノードに送信
            try:
                tx_hash = web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as err:
                result.append({
                    'id': i + 1,
                    'status': 0,
                })
                LOG.error(f"Send transaction failed: {err}")
                continue

            # 実行結果を確認
            try:
                tx = web3.eth.waitForTransactionReceipt(tx_hash, 30)
            except Exception as err:
                # NOTE: eth.waitForTransactionReceiptは本来はExceptionではなくNoneを返す仕様だが、
                #       バグでExceptionを返すようになっているため対応しておく
                LOG.error(f"Transaction failed: {err}")
                tx = None

            if tx is None:
                result.append({
                    'id': i + 1,
                    'status': 0,
                })
            else:
                result.append({
                    'id': i + 1,
                    'status': tx['status'],
                })

        self.on_success(res, result)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'raw_tx_hex_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json


# ------------------------------
# sendRawTransaction (No Wait)
# ------------------------------
class SendRawTransactionNoWait(BaseResource):
    """
    Handle for endpoint: /v2/Eth/SendRawTransactionNoWait
    """

    def on_post(self, req, res):
        LOG.info('v2.eth.SendRawTransactionNoWait')

        session = req.context["session"]

        request_json = SendRawTransactionNoWait.validate(req)
        raw_tx_hex_list = request_json['raw_tx_hex_list']

        # トークン取扱状態チェック
        # トランザクション送信前にトークンの取扱状態をチェックする
        for raw_tx_hex in raw_tx_hex_list:
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address('0x' + raw_tx[3].hex())
            except Exception as err:
                LOG.info(f"RLP decoding failed: {err}")
                continue

            listed_token = session.query(Listing). \
                filter(Listing.token_address == to_contract_address). \
                first()
            private_listed_token = session.query(PrivateListing). \
                filter(PrivateListing.token_address == to_contract_address). \
                first()
            if listed_token is not None or private_listed_token is not None:
                TokenContract = Contract.get_contract("IbetStandardTokenInterface", to_contract_address)
                try:
                    if TokenContract.functions.status().call() is False:
                        raise SuspendedTokenError("Token is currently suspended")
                except Exception as err:
                    LOG.exception(f"{err}")

        # トランザクション送信
        result = []
        for i, raw_tx_hex in enumerate(raw_tx_hex_list):
            # 実行コントラクトのアドレスを取得
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address('0x' + raw_tx[3].hex())
                LOG.info(raw_tx)
            except Exception as err:
                result.append({'id': i + 1, 'status': 0})
                LOG.error(f"RLP decoding failed: {err}")
                continue

            # 実行可能コントラクトであることをチェック
            executable_contract = session.query(ExecutableContract). \
                filter(to_contract_address == ExecutableContract.contract_address). \
                first()
            if executable_contract is None:
                result.append({'id': i + 1, 'status': 0})
                LOG.error('Not executable')
                continue

            # ブロックチェーンノードに送信
            try:
                web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as err:
                result.append({
                    'id': i + 1,
                    'status': 0,
                })
                LOG.error(f"Send transaction failed: {err}")
                continue

        self.on_success(res, result)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'raw_tx_hex_list': {
                'type': 'list',
                'empty': False,
                'required': True,
                'schema': {
                    'type': 'string',
                    'required': True,
                    'empty': False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
