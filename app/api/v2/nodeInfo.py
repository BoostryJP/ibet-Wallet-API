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
import json

from web3 import Web3

from app import (
    config,
    log
)
from app.api.common import BaseResource
from app.model.node import Node

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))


# ------------------------------
# ノード情報
# ------------------------------
class NodeInfo(BaseResource):
    """
    Endpoint: /NodeInfo
    """

    def on_get(self, req, res):
        LOG.info('v2.nodeInfo.GetNodeInfo')

        payment_gateway_json = json.load(open("app/contracts/json/PaymentGateway.json", "r"))
        personal_info_json = json.load(open("app/contracts/json/PersonalInfo.json", "r"))
        ibet_exchange_json = json.load(open("app/contracts/json/IbetExchange.json", "r"))
        ibet_escrow_json = json.load(open("app/contracts/json/IbetEscrow.json", "r"))
        e2e_messaging_json = json.load(open("app/contracts/json/E2EMessaging.json", "r"))

        nodeInfo = {
            'payment_gateway_address': config.PAYMENT_GATEWAY_CONTRACT_ADDRESS,
            'payment_gateway_abi': payment_gateway_json['abi'],
            'personal_info_address': config.PERSONAL_INFO_CONTRACT_ADDRESS,
            'personal_info_abi': personal_info_json['abi'],
            'ibet_straightbond_exchange_address': config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_straightbond_exchange_abi': ibet_exchange_json['abi'],
            'ibet_membership_exchange_address': config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_membership_exchange_abi': ibet_exchange_json['abi'],
            'ibet_coupon_exchange_address': config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_coupon_exchange_abi': ibet_exchange_json['abi'],
            'ibet_share_exchange_address': config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_share_exchange_abi': ibet_exchange_json['abi'],
            'ibet_escrow_address': config.IBET_ESCROW_CONTRACT_ADDRESS,
            'ibet_escrow_abi': ibet_escrow_json['abi'],
            'e2e_messaging_address': config.E2E_MESSAGING_CONTRACT_ADDRESS,
            'e2e_messaging_abi': e2e_messaging_json['abi'],
            'agent_address': config.AGENT_ADDRESS,
        }

        self.on_success(res, nodeInfo)


# ------------------------------
# ブロック同期情報
# ------------------------------
class BlockSyncStatus(BaseResource):
    """
    Endpoint: /NodeInfo/BlockSyncStatus
    """

    def on_get(self, req, res):
        LOG.info('v2.nodeInfo.GetBlockSyncStatus')

        session = req.context["session"]

        # Get block sync status
        node = session.query(Node).first()

        # Get latest block number
        latest_block_number = None
        if node.is_synced:
            latest_block_number = web3.eth.blockNumber

        self.on_success(res, {
            "is_synced": node.is_synced,
            "latest_block_number": latest_block_number
        })
