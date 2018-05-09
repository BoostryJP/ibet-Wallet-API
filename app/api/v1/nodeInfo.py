import os

from app import log, config
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

        nodeInfo = {
            'white_list_address': os.environ.get('WHITE_LIST_CONTRACT_ADDRESS'),
            'white_list_abi': config.WHITE_LIST_CONTRACT_ABI,

            'personal_info_address': os.environ.get('PERSONAL_INFO_CONTRACT_ADDRESS'),
            'personal_info_abi': config.PERSONAL_INFO_CONTRACT_ABI,

            'ibet_exchange_address': os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS'),
            'ibet_exchange_abi': config.IBET_EXCHANGE_CONTRACT_ABI,
        }

        self.on_success(res, nodeInfo)
