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
