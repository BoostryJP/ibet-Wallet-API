import json

from app import config
from app import log
from app.api.common import BaseResource

LOG = log.get_logger()


# ------------------------------
# ノード情報
# ------------------------------
class NodeInfo(BaseResource):
    """
    Handle for endpoint: /NodeInfo
    """

    def on_get(self, req, res):
        LOG.info('v2.nodeInfo.GetNodeInfo')

        contracts = json.load(open('data/contracts.json', 'r'))

        nodeInfo = {
            'payment_gateway_address': config.PAYMENT_GATEWAY_CONTRACT_ADDRESS,
            'payment_gateway_abi': contracts['PaymentGateway']['abi'],
            'personal_info_address': config.PERSONAL_INFO_CONTRACT_ADDRESS,
            'personal_info_abi': contracts['PersonalInfo']['abi'],
            'ibet_straightbond_exchange_address': config.IBET_SB_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_straightbond_exchange_abi': contracts['IbetStraightBondExchange']['abi'],
            'ibet_membership_exchange_address': config.IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_membership_exchange_abi': contracts['IbetMembershipExchange']['abi'],
            'ibet_coupon_exchange_address': config.IBET_CP_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_coupon_exchange_abi': contracts['IbetCouponExchange']['abi'],
            'ibet_otc_exchange_address': config.IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS,
            'ibet_otc_exchange_abi': contracts['IbetOTCExchange']['abi'],
            'agent_address': config.AGENT_ADDRESS,
        }

        self.on_success(res, nodeInfo)
