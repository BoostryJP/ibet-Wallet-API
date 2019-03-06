import os
import json

from app import log
from app.api.common import BaseResource

LOG = log.get_logger()

# ------------------------------
# ノード情報
# ------------------------------
class NodeInfo(BaseResource):
    '''
    Handle for endpoint: /v1/NodeInfo
    '''
    def on_get(self, req, res):
        LOG.info('v1.nodeInfo.GetNodeInfo')

        contracts = json.load(open('data/contracts.json' , 'r'))

        nodeInfo = {
            'payment_gateway_address': os.environ.get('PAYMENT_GATEWAY_CONTRACT_ADDRESS'),
            'payment_gateway_abi': contracts['PaymentGateway']['abi'],

            'personal_info_address': os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS'),
            'personal_info_abi': contracts['PersonalInfo']['abi'],

            'ibet_exchange_address': os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'),
            'ibet_exchange_abi': contracts['IbetStraightBondExchange']['abi'],

            'ibet_membership_exchange_address': os.environ.get('IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS'),
            'ibet_membership_exchange_abi': contracts['IbetMembershipExchange']['abi'],

            'ibet_coupon_exchange_address': os.environ.get('IBET_CP_EXCHANGE_CONTRACT_ADDRESS'),
            'ibet_coupon_exchange_abi': contracts['IbetCouponExchange']['abi'],

            'agent_address': os.environ.get('AGENT_ADDRESS'),
        }

        self.on_success(res, nodeInfo)
