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
from cerberus import Validator
from eth_utils import to_checksum_address
from sqlalchemy import desc
from web3 import Web3

from app import log
from app.api.common import BaseResource
from app.errors import (
    InvalidParameterError,
    DataNotExistsError
)
from app import config
from app.contracts import Contract
from app.model.db import Listing
from app.model.blockchain import (
    BondToken,
    MembershipToken,
    CouponToken,
    ShareToken
)
from app.utils.company_list import CompanyList

LOG = log.get_logger()


# ------------------------------
# 発行会社情報参照
# ------------------------------
class CompanyInfo(BaseResource):
    """
    Endpoint: /Company/{eth_address}
    """

    def on_get(self, req, res, eth_address=None, **kwargs):
        LOG.info('v2.company.CompanyInfo')

        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        company = CompanyList.get_find(to_checksum_address(eth_address))
        if company.address == "":
            raise DataNotExistsError('eth_address: %s' % eth_address)

        self.on_success(res, company.json())


# ------------------------------
# 発行会社一覧参照
# ------------------------------
class CompanyInfoList(BaseResource):
    """
    Endpoint: /v2/Companies
    """

    def on_get(self, req, res, **kwargs):
        LOG.info('v2.company.CompanyInfoList')

        session = req.context["session"]

        # Validation
        request_json = self.validate(req)
        include_private_listing = True if request_json["include_private_listing"] == "true" else False

        # Get company list
        _company_list = CompanyList.get()
        company_list = [company.json() for company in _company_list.all()]

        # Get the token listed
        if include_private_listing:
            available_tokens = session.query(Listing).all()
        else:
            available_tokens = session.query(Listing).filter(Listing.is_public == True).all()

        # Filter only issuers that issue the listed tokens
        listing_owner_list = []
        for token in available_tokens:
            try:
                token_address = to_checksum_address(token.token_address)
                token_contract = Contract.get_contract(
                    contract_name="Ownable",
                    address=token_address
                )
                owner_address = Contract.call_function(
                    contract=token_contract,
                    function_name="owner",
                    args=(),
                    default_returns=config.ZERO_ADDRESS
                )
                listing_owner_list.append(owner_address)
            except Exception as e:
                LOG.warning(e)

        has_listing_owner_function = self.has_listing_owner_function_creator(listing_owner_list)
        filtered_company_list = filter(has_listing_owner_function, company_list)

        self.on_success(res, list(filtered_company_list))

    @staticmethod
    def validate(req):
        request_json = {
            "include_private_listing": req.get_param("include_private_listing")
        }

        validator = Validator({
            "include_private_listing": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["true", "false"],
            }
        })
        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document

    @staticmethod
    def has_listing_owner_function_creator(listing_owner_list):
        def has_listing_owner_function(company_info):
            for address in listing_owner_list:
                if to_checksum_address(company_info['address']) == address:
                    return True
            return False
        return has_listing_owner_function


# ------------------------------
# 発行会社のトークン一覧
# ------------------------------
class CompanyTokenList(BaseResource):
    """
    Endpoint: /v2/Company/{eth_address}/Tokens
    """

    def on_get(self, req, res, eth_address=None, **kwargs):
        LOG.info('v2.company.CompanyTokenList')
        session = req.context['session']

        # Validation
        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        request_json = self.validate(req)
        include_private_listing = True if request_json["include_private_listing"] == "true" else False

        # TokenList contract
        list_contract = Contract.get_contract(
            contract_name='TokenList',
            address=config.TOKEN_LIST_CONTRACT_ADDRESS
        )

        # Get the token listed
        if include_private_listing:
            available_list = session.query(Listing). \
                filter(Listing.owner_address == eth_address). \
                order_by(desc(Listing.id)). \
                all()
        else:
            available_list = session.query(Listing). \
                filter(Listing.owner_address == eth_address). \
                filter(Listing.is_public == True). \
                order_by(desc(Listing.id)). \
                all()

        # Get token attributes
        token_list = []
        for available_token in available_list:
            token_address = to_checksum_address(available_token.token_address)
            token_info = Contract.call_function(
                contract=list_contract,
                function_name="getTokenByAddress",
                args=(token_address,),
                default_returns=(config.ZERO_ADDRESS, "", config.ZERO_ADDRESS)
            )
            # Only those items published in TokenList will be processed
            if token_info[0] != config.ZERO_ADDRESS:
                token_template = token_info[1]
                # Filter only the token types used in the system
                if self.available_token_template(token_template):
                    token_model = self.get_token_model(token_template)
                    token = token_model.get(session=session, token_address=token_address)
                    token_list.append(token.__dict__)
                else:
                    continue

        self.on_success(res, token_list)

    @staticmethod
    def validate(req):
        request_json = {
            "include_private_listing": req.get_param("include_private_listing")
        }

        validator = Validator({
            "include_private_listing": {
                "type": "string",
                "required": False,
                "nullable": True,
                "allowed": ["true", "false"],
            }
        })
        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document

    @staticmethod
    def available_token_template(token_template: str) -> bool:
        """Availability of token type

        :param token_template: Token type
        :return: available (True) or not available (False)
        """
        if token_template == "IbetShare":
            return config.SHARE_TOKEN_ENABLED
        elif token_template == "IbetStraightBond":
            return config.BOND_TOKEN_ENABLED
        elif token_template == "IbetMembership":
            return config.MEMBERSHIP_TOKEN_ENABLED
        elif token_template == "IbetCoupon":
            return config.COUPON_TOKEN_ENABLED
        else:
            return False

    @staticmethod
    def get_token_model(token_template: str):
        """Get token model

        :param token_template: Token type
        :return: Token model
        """
        if token_template == "IbetShare":
            return ShareToken
        elif token_template == "IbetStraightBond":
            return BondToken
        elif token_template == "IbetMembership":
            return MembershipToken
        elif token_template == "IbetCoupon":
            return CouponToken
        else:
            return False
