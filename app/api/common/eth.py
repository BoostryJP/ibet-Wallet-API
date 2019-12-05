# -*- coding: utf-8 -*-
from cerberus import Validator

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address
from rlp import decode
from hexbytes import HexBytes

from app import log
from app.api.common import BaseResource
from app.errors import InvalidParameterError
from app import config
from app.model import ExecutableContract

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# nonce取得
# ------------------------------
class GetTransactionCount(BaseResource):
    """
    Handle for endpoint: /v1/Eth/TransactionCount/{eth_address}
    """

    def on_get(self, req, res, eth_address):
        LOG.info('v1.Eth.GetTransactionCount')

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
    Handle for endpoint: /v1/Eth/SendRawTransaction
    """

    def on_post(self, req, res):
        LOG.info('v1.Eth.SendRawTransaction')

        session = req.context["session"]

        request_json = SendRawTransaction.validate(req)
        raw_tx_hex_list = request_json['raw_tx_hex_list']

        result = []

        for i, raw_tx_hex in enumerate(raw_tx_hex_list):
            # 実行コントラクトのアドレスを取得
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address('0x' + raw_tx[3].hex())
            except Exception as e:
                result.append({'id': i + 1, 'status': 0})
                LOG.error(e)
                LOG.error('RLP decoding failed')
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
            except ValueError as e:
                result.append({
                    'id': i + 1,
                    'status': 0,
                })
                LOG.error(e)
                continue

            # 実行結果を確認
            try:
                tx = web3.eth.waitForTransactionReceipt(tx_hash, 30)
            except Exception as e:
                # NOTE: eth.waitForTransactionReceiptは本来はExceptionではなくNoneを返す仕様だが、
                #       バグでExceptionを返すようになっているため対応しておく
                LOG.error(e)
                tx = None
                pass

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
