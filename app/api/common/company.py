# -*- coding: utf-8 -*-
import json
import requests
import os

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config
from app.contracts import Contract
from app.model import Listing

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
    Handle for endpoint: /v1/Company/{eth_address}
    """

    def on_get(self, req, res, eth_address):
        LOG.info('common.Company.CompanyInfo')

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
        LOG.info('common.Company.CompanyInfoList')

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

        # TokenList-Contractへの接続
        ListContract = Contract.get_contract(
            'TokenList', config.TOKEN_LIST_CONTRACT_ADDRESS)

        # 取扱トークンのownerAddressと会社リストを突合
        listing_owner_list = []
        for token in available_tokens:
            token_address = to_checksum_address(token.token_address)
            owner_address = ListContract.functions.getOwnerAddress(token_address).call()
            listing_owner_list.append(owner_address)
        has_listing_owner_function = self.has_listing_owner_function_creator(listing_owner_list)
        filtered_company_list = filter(has_listing_owner_function, company_list)

        self.on_success(res, list(filtered_company_list))

    @staticmethod
    def has_listing_owner_function_creator(listing_owner_list):
        def has_listing_owner_function(company_info):
            for address in listing_owner_list:
                if company_info['address'] == address:
                    return True
            return False
        return has_listing_owner_function


# ------------------------------
# 決済代行業者情報参照
# ------------------------------
class PaymentAgentInfo(BaseResource):
    """
    Handle for endpoint: /v1/PaymentAgent/{eth_address}
    """

    def on_get(self, req, res, eth_address):
        LOG.info('common.Company.PaymentAgent')

        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        isExist = False
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/payment_agent_list.json', 'r'))
            else:
                company_list = \
                    requests.get(config.PAYMENT_AGENT_LIST_URL, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as err:
            LOG.error('Failed To Get Data: %s', err)
            raise AppError

        for company_info in company_list:
            if to_checksum_address(company_info['address']) == to_checksum_address(eth_address):
                isExist = True
                self.on_success(res, company_info)
        if not isExist:
            raise DataNotExistsError('eth_address: %s' % eth_address)
