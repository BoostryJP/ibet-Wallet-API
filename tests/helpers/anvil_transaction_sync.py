"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast
from unittest import mock

from hexbytes import HexBytes
from web3.types import RPCEndpoint

from tests.helpers import contract as contract_helper


@contextmanager
def install_anvil_transaction_sync_patch() -> Iterator[None]:
    """Route transaction sending through Anvil's sync RPC in tests.

    The patch preserves the normal web3.py API shape while avoiding repeated
    receipt polling in test code that already expects mined transactions.
    """

    transaction_receipt_cache: dict[HexBytes, Any] = {}
    original_contract_get_transaction_receipt = (
        contract_helper.web3.eth.get_transaction_receipt
    )

    def _cache_receipt(receipt: Any) -> HexBytes:
        transaction_hash = HexBytes(receipt["transactionHash"])
        transaction_receipt_cache[transaction_hash] = receipt
        return transaction_hash

    def _make_send_transaction_patch(web3_instance: Any):
        def _send_transaction_via_sync_api(transaction: Any) -> HexBytes:
            transaction_params = web3_instance.eth.send_transaction_munger(transaction)[
                0
            ]
            receipt = web3_instance.manager.request_blocking(
                cast(RPCEndpoint, "eth_sendTransactionSync"), [transaction_params]
            )
            return _cache_receipt(receipt)

        return _send_transaction_via_sync_api

    def _make_get_transaction_receipt_patch(original_getter: Any):
        def _get_transaction_receipt_with_cache(transaction_hash: HexBytes) -> Any:
            cached_receipt = transaction_receipt_cache.get(HexBytes(transaction_hash))
            if cached_receipt is not None:
                return cached_receipt
            return original_getter(transaction_hash)

        return _get_transaction_receipt_with_cache

    with (
        mock.patch.object(
            contract_helper.web3.eth,
            "send_transaction",
            _make_send_transaction_patch(contract_helper.web3),
        ),
        mock.patch.object(
            contract_helper.web3.eth,
            "get_transaction_receipt",
            _make_get_transaction_receipt_patch(
                original_contract_get_transaction_receipt
            ),
        ),
    ):
        yield
