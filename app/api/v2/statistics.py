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
from sqlalchemy import (
    func,
    or_
)
from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model.db import (
    IDXPosition,
    Listing
)
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)

LOG = log.get_logger()


# /Statistics/Token/{contract_address}
class Token(BaseResource):
    """トークン別統計値取得"""

    def on_get(self, req, res, contract_address=None, **kwargs):
        LOG.info('v2.statistics.Token')

        session = req.context["session"]

        # Validation
        try:
            contract_address = to_checksum_address(contract_address)
            if not Web3.isAddress(contract_address):
                description = 'invalid contract_address'
                raise InvalidParameterError(description=description)
        except:
            description = 'invalid contract_address'
            raise InvalidParameterError(description=description)

        # Get issuer address
        row = session.query(Listing.owner_address).\
            filter(Listing.token_address == contract_address).\
            first()
        if row is not None:
            owner_address = row[0]
        else:
            raise DataNotExistsError('contract_address: %s' % contract_address)


        # Get holders count
        holders_count = session.query(func.count()). \
            filter(IDXPosition.token_address == contract_address). \
            filter(IDXPosition.account_address != owner_address). \
            filter(or_(
                IDXPosition.balance > 0,
                IDXPosition.pending_transfer > 0,
                IDXPosition.exchange_balance > 0,
                IDXPosition.exchange_commitment > 0)). \
            first()

        res_data = {
            'holders_count': holders_count[0]
        }

        self.on_success(res, res_data)
