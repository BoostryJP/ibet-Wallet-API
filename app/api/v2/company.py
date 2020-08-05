# -*- coding: utf-8 -*-
import json
import requests

from eth_utils import to_checksum_address
from sqlalchemy import desc

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config
from app.contracts import Contract
from app.model import Listing, BondToken, MembershipToken, CouponToken, ShareToken

LOG = log.get_logger()

from web3 import Web3
from web3.middleware import geth_poa_middleware

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


# ------------------------------
# 発行会社情報参照
# ------------------------------
class CompanyInfo(BaseResource):
    """
    Handle for endpoint: /Company/{eth_address}
    """

    def on_get(self, req, res, eth_address):
        LOG.info('v2.company.CompanyInfo')

        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        isExist = False

        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as err:
            LOG.error('Failed To Get Data: %s', err)
            raise AppError

        for company_info in company_list:
            if to_checksum_address(company_info['address']) == \
                    to_checksum_address(eth_address):
                isExist = True
                self.on_success(res, company_info)
        if not isExist:
            raise DataNotExistsError('eth_address: %s' % eth_address)


# ------------------------------
# 発行会社一覧参照
# ------------------------------
class CompanyInfoList(BaseResource):
    """
    Handle for endpoint: /v2/Companies
    """

    def on_get(self, req, res):
        LOG.info('v2.company.CompanyInfoList')

        session = req.context["session"]

        # 会社リストを取得
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as err:
            LOG.error('Failed To Get Data: %s', err)
            raise AppError

        # 取扱トークンリストを取得
        available_tokens = session.query(Listing).all()

        # 取扱トークンのownerAddressと会社リストを突合
        listing_owner_list = []
        for token in available_tokens:
            try:
                token_address = to_checksum_address(token.token_address)
                token_contract = Contract.get_contract('IbetStandardTokenInterface', token_address)
                owner_address = token_contract.functions.owner().call()
                listing_owner_list.append(owner_address)
            except Exception as e:
                LOG.warning(e)
                pass
        has_listing_owner_function = self.has_listing_owner_function_creator(listing_owner_list)
        filtered_company_list = filter(has_listing_owner_function, company_list)

        self.on_success(res, list(filtered_company_list))

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
    Handle for endpoint: /v2/Company/{eth_address}/Tokens
    """

    def on_get(self, req, res, eth_address=None):
        LOG.info('v2.company.CompanyTokenList')

        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        session = req.context['session']

        ListContract = Contract.get_contract('TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # 取扱トークンリストを取得
        available_list = session.query(Listing).\
            filter(Listing.owner_address == eth_address).\
            order_by(desc(Listing.id)).\
            all()

        token_list = []
        for available_token in available_list:
            token_address = to_checksum_address(available_token.token_address)
            token_info = ListContract.functions.getTokenByAddress(token_address).call()
            if token_info[0] != config.ZERO_ADDRSS:  # TokenListに公開されているもののみを対象とする
                token_template = token_info[1]
                if self.available_token_template(token_template):  # 取扱対象のトークン種別のみ対象とする
                    token_model = self.get_token_model(token_template)
                    token = token_model.get(session=session, token_address=token_address)
                    token_list.append(token.__dict__)
                else:
                    continue

        self.on_success(res, token_list)

    @staticmethod
    def available_token_template(token_template: str) -> bool:
        """
        取扱トークン種別判定

        :param token_template: トークン種別
        :return: 判定結果（Boolean）
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
        """
        トークンModelの取得

        :param token_template: トークン種別
        :return: 商品別のトークンモデル
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


# ------------------------------
# 決済代行業者情報参照
# ------------------------------
# 後方互換性用API. 代替は CompanyInfo
class PaymentAgentInfo(BaseResource):
    """
    Handle for endpoint: /PaymentAgent/{eth_address}
    """

    def on_get(self, req, res, eth_address):
        LOG.info('v2.company.PaymentAgent')

        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        isExist = False
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.COMPANY_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as err:
            LOG.error('Failed To Get Data: %s', err)
            raise AppError

        for company_info in company_list:
            if to_checksum_address(company_info['address']) == to_checksum_address(eth_address):
                isExist = True
                self.on_success(res, company_info)
        if not isExist:
            raise DataNotExistsError('eth_address: %s' % eth_address)
