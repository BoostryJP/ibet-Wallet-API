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

from app import config
from app import log
from app.api.common import BaseResource
from app.model.node import Node

LOG = log.get_logger()


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
        ibet_straightbond_exchange_json = json.load(open("app/contracts/json/IbetStraightBondExchange.json", "r"))
        ibet_membership_exchange_json = json.load(open("app/contracts/json/IbetMembershipExchange.json", "r"))
        ibet_coupon_exchange_json = json.load(open("app/contracts/json/IbetCouponExchange.json", "r"))
        ibet_otc_exchange_json = json.load(open("app/contracts/json/IbetOTCExchange.json", "r"))

        nodeInfo = {
            'payment_gateway_address': config.PAYMENT_GATEWAY_CONTRACT_ADDRESS,
            'payment_gateway_abi': payment_gateway_json['abi'],
            'personal_info_address': config.PERSONAL_INFO_CONTRACT_ADDRESS,
            'personal_info_abi': personal_info_json['abi'],
            'ibet_straightbond_exchange_address': config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_straightbond_exchange_abi': ibet_straightbond_exchange_json['abi'],
            'ibet_membership_exchange_address': config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_membership_exchange_abi': ibet_membership_exchange_json['abi'],
            'ibet_coupon_exchange_address': config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_coupon_exchange_abi': ibet_coupon_exchange_json['abi'],
            'ibet_otc_exchange_address': config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_otc_exchange_abi': ibet_otc_exchange_json['abi'],
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

        node = session.query(Node).first()

        self.on_success(res, {
            "is_synced": node.is_synced
        })
