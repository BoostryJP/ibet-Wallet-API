# -*- coding: utf-8 -*-
from sqlalchemy import func

from web3 import Web3
from web3.middleware import geth_poa_middleware

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.contracts import Contract
from app.model import Position, Listing, PrivateListing
from app.errors import InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# トークン別統計値取得
# ------------------------------
class Token(BaseResource):
    """
    Endpoint: /v2/Statistics/Token/{contract_address}
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

        # 発行体アドレス取得
        row = session.query(Listing.owner_address).filter(Listing.token_address == contract_address). \
            union_all(
            session.query(PrivateListing.owner_address).filter(PrivateListing.token_address == contract_address)). \
            first()
        if row is not None:
            owner_address = row[0]
        else:
            raise DataNotExistsError('contract_address: %s' % contract_address)

        # DEXアドレス取得
        TokenContract = Contract.get_contract('IbetStandardTokenInterface', contract_address)
        dex_address = TokenContract.functions.tradableExchange().call()

        # 保有者数取得
        holders_count = session.query(func.count()). \
            filter(Position.token_address == contract_address). \
            filter(Position.account_address != owner_address). \
            filter(Position.account_address != dex_address). \
            filter(Position.balance > 0). \
            first()

        res_data = {
            'holders_count': holders_count[0]
        }

        self.on_success(res, res_data)
