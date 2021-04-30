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
from web3.geth import GethTxPool
from web3.middleware import geth_poa_middleware
from web3.exceptions import TimeExhausted
from eth_account import Account
from eth_typing import ChecksumAddress
from eth_utils import to_checksum_address
from rlp import decode
from hexbytes import HexBytes

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    SuspendedTokenError,
    DataNotExistsError,
    ServiceUnavailable
)
from app import config
from app.model import ExecutableContract, Listing
from app.contracts import Contract
from app.model.node import Node

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_onion.inject(geth_poa_middleware, layer=0)


# ------------------------------
# nonce取得
# ------------------------------
class GetTransactionCount(BaseResource):
    """
    Endpoint: /Eth/TransactionCount/{eth_address}
    """

    def on_get(self, req, res, eth_address: ChecksumAddress = None):
        LOG.info('v2.eth.GetTransactionCount')

        try:
            eth_address = to_checksum_address(eth_address)
        except ValueError:
            raise InvalidParameterError

        # 入力値チェック
        request_json = self.validate(req)

        nonce = web3.eth.getTransactionCount(
            to_checksum_address(eth_address),
            block_identifier=request_json["block_identifier"]
        )
        gasprice = web3.eth.gasPrice
        chainid = config.WEB3_CHAINID

        eth_info = {'nonce': nonce, 'gasprice': gasprice, 'chainid': chainid}
        self.on_success(res, eth_info)

    @staticmethod
    def validate(req):
        request_json = {
            "block_identifier": req.get_param("block_identifier", default=None),
        }

        validator = Validator({
            "block_identifier": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["latest", "earliest", "pending"]
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document


# ------------------------------
# sendRawTransaction
# ------------------------------
class SendRawTransaction(BaseResource):
    """
    Endpoint: /Eth/SendRawTransaction
    """

    def on_post(self, req, res):
        LOG.info("v2.eth.SendRawTransaction")

        session = req.context["session"]

        request_json = SendRawTransaction.validate(req)
        raw_tx_hex_list = request_json["raw_tx_hex_list"]

        # Get TokenList Contract
        ListContract = Contract.get_contract(
            "TokenList",
            config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Check token status
        # NOTE: Check the token status before sending a transaction.
        for raw_tx_hex in raw_tx_hex_list:
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address("0x" + raw_tx[3].hex())
            except Exception as err:
                LOG.info(f"RLP decoding failed: {err}")
                continue

            listed_token = session.query(Listing). \
                filter(Listing.token_address == to_contract_address). \
                first()

            if listed_token is not None:
                LOG.info(f"Token Address: {to_contract_address}")
                token_attribute = ListContract.functions.getTokenByAddress(to_contract_address).call()
                if token_attribute[1] != "":
                    try:
                        TokenContract = Contract.get_contract(token_attribute[1], to_contract_address)
                    except Exception as err:
                        LOG.warning(f"Could not get token status: {err}")
                        continue
                    if TokenContract.functions.status().call() is False:
                        raise SuspendedTokenError("Token is currently suspended")

        # Check block synchronization state
        # NOTE: If the block is out of sync, the nonce is not the correct value.
        block = session.query(Node).first()
        if block is None or not block.is_synced:
            raise ServiceUnavailable("Block synchronization is down")

        # Send transaction
        result = []
        for i, raw_tx_hex in enumerate(raw_tx_hex_list):
            # Get the contract address of the execution target.
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address("0x" + raw_tx[3].hex())
                LOG.info(raw_tx)
            except Exception as err:
                result.append({"id": i + 1, "status": 0})
                LOG.error(f"RLP decoding failed: {err}")
                continue

            # Check that contract is executable
            executable_contract = session.query(ExecutableContract). \
                filter(to_contract_address == ExecutableContract.contract_address). \
                first()
            if executable_contract is None:
                # If it is not a default contract, return error status.
                if to_contract_address != config.PAYMENT_GATEWAY_CONTRACT_ADDRESS and \
                        to_contract_address != config.PERSONAL_INFO_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS:
                    result.append({"id": i + 1, "status": 0})
                    LOG.error("Not executable")
                    continue

            # Send raw transaction
            try:
                tx_hash = web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as err:
                result.append({
                    "id": i + 1,
                    "status": 0,
                })
                LOG.error(f"Send transaction failed: {err}")
                continue

            # Handling a transaction execution result
            try:
                tx = web3.eth.waitForTransactionReceipt(tx_hash, timeout=config.TRANSACTION_WAIT_TIMEOUT)
            except TimeExhausted as err:
                status = 2  # execution success (pending transaction)

                # Transactions that are not promoted to pending and remain in the queued state
                # will return an error status.
                try:
                    from_address = Account.recoverTransaction(raw_tx_hex)
                except Exception as err:
                    result.append({"id": i + 1, "status": 0})
                    LOG.error(f"get sender address from signed transaction failed: {err}")
                    continue
                nonce = int("0x0" if raw_tx[0].hex() == "" else raw_tx[0].hex(), 16)
                txpool_inspect = GethTxPool.inspect
                if from_address in txpool_inspect.queued:
                    if str(nonce) in txpool_inspect.queued[from_address]:
                        status = 0  # execution failure

                result.append({
                    "id": i + 1,
                    "status": status,
                })
                LOG.warning(f"Transaction receipt timeout: {err}")
                continue
            except Exception as err:
                result.append({
                    "id": i + 1,
                    "status": 0,
                })
                LOG.error(f"Transaction failed: {err}")
                continue

            result.append({
                "id": i + 1,
                "status": tx["status"],
            })

        self.on_success(res, result)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "raw_tx_hex_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
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
    Endpoint: /v2/Eth/SendRawTransactionNoWait
    """

    def on_post(self, req, res):
        LOG.info("v2.eth.SendRawTransactionNoWait")

        session = req.context["session"]

        request_json = SendRawTransactionNoWait.validate(req)
        raw_tx_hex_list = request_json["raw_tx_hex_list"]

        # Get TokenList Contract
        ListContract = Contract.get_contract(
            "TokenList",
            config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Check token status
        # NOTE: Check the token status before sending a transaction.
        for raw_tx_hex in raw_tx_hex_list:
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address("0x" + raw_tx[3].hex())
            except Exception as err:
                LOG.info(f"RLP decoding failed: {err}")
                continue

            listed_token = session.query(Listing). \
                filter(Listing.token_address == to_contract_address). \
                first()

            if listed_token is not None:
                LOG.info(f"Token Address: {to_contract_address}")
                token_attribute = ListContract.functions.getTokenByAddress(to_contract_address).call()
                if token_attribute[1] != "":
                    try:
                        TokenContract = Contract.get_contract(token_attribute[1], to_contract_address)
                    except Exception as err:
                        LOG.warning(f"Could not get token status: {err}")
                        continue
                    if TokenContract.functions.status().call() is False:
                        raise SuspendedTokenError("Token is currently suspended")

        # Check block synchronization state
        # NOTE: If the block is out of sync, the nonce is not the correct value.
        node = session.query(Node).first()
        if node is None or not node.is_synced:
            raise ServiceUnavailable("Block synchronization is down")

        # Send transaction
        result = []
        for i, raw_tx_hex in enumerate(raw_tx_hex_list):
            # Get the contract address of the execution target.
            try:
                raw_tx = decode(HexBytes(raw_tx_hex))
                to_contract_address = to_checksum_address("0x" + raw_tx[3].hex())
                LOG.info(raw_tx)
            except Exception as err:
                result.append({"id": i + 1, "status": 0})
                LOG.error(f"RLP decoding failed: {err}")
                continue

            # Check that contract is executable
            executable_contract = session.query(ExecutableContract). \
                filter(to_contract_address == ExecutableContract.contract_address). \
                first()
            if executable_contract is None:
                # If it is not a default contract, return error status.
                if to_contract_address != config.PAYMENT_GATEWAY_CONTRACT_ADDRESS and \
                        to_contract_address != config.PERSONAL_INFO_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS and \
                        to_contract_address != config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS:
                    result.append({"id": i + 1, "status": 0})
                    LOG.error("Not executable")
                    continue

            # Send raw transaction
            try:
                transaction_hash = web3.eth.sendRawTransaction(raw_tx_hex)
            except ValueError as err:
                result.append({
                    "id": i + 1,
                    "status": 0,
                    "transaction_hash": None
                })
                LOG.error(f"Send transaction failed: {err}")
                continue

            result.append({
                "id": i + 1,
                "status": 1,
                "transaction_hash": transaction_hash.hex()
            })

        self.on_success(res, result)

    @staticmethod
    def validate(req):
        request_json = req.context["data"]
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "raw_tx_hex_list": {
                "type": "list",
                "empty": False,
                "required": True,
                "schema": {
                    "type": "string",
                    "required": True,
                    "empty": False,
                }
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json


# ------------------------------
# waitForTransactionReceipt
# ------------------------------
class WaitForTransactionReceipt(BaseResource):
    """
    Endpoint: /Eth/WaitForTransactionReceipt
    """

    def on_post(self, req, res):
        LOG.info('v2.eth.WaitForTransactionReceipt')

        request_json = self.validate(req)
        transaction_hash = request_json.get("transaction_hash")
        timeout = request_json.get("timeout", 5)

        # transaction receipt の監視
        try:
            tx = web3.eth.waitForTransactionReceipt(
                transaction_hash=transaction_hash,
                timeout=timeout
            )
        except Exception as err:
            raise DataNotExistsError

        if tx is None:
            raise DataNotExistsError

        self.on_success(res)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            "transaction_hash": {
                "type": "string",
                "required": True,
                "empty": False,
            },
            "timeout": {
                "type": "integer",
                "min": 1,
                "max": 30
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
