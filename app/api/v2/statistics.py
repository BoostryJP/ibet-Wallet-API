# -*- coding: utf-8 -*-
from sqlalchemy import func

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import Position
from app.errors import InvalidParameterError
from app import config

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# トークン別統計値取得
# ------------------------------
class Token(BaseResource):
    """
    Handle for endpoint: /v2/Statistics/Token/{contract_address}
    """

    def on_get(self, req, res, contract_address=None):
        LOG.info('v2.statistics.Token')

        session = req.context["session"]

        # 入力値チェック
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                description = 'invalid contract_address'
                raise InvalidParameterError(description=description)
        except:
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)

        # 保有者数取得
        holders_count = session.query(func.count()). \
            filter(Position.token_address == contract_address). \
            filter(Position.balance > 0). \
            first()

        res_data = {
            'holders_count': holders_count[0]
        }

        self.on_success(res, res_data)
