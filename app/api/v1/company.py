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
        LOG.info('v1.Company.CompanyInfo')

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
# 決済代行業者情報参照
# ------------------------------
class PaymentAgentInfo(BaseResource):
    """
    Handle for endpoint: /v1/PaymentAgent/{eth_address}
    """

    def on_get(self, req, res, eth_address):
        LOG.info('v1.Company.PaymentAgent')

        if not Web3.isAddress(eth_address):
            description = 'invalid eth_address'
            raise InvalidParameterError(description=description)

        agent_address = to_checksum_address(eth_address)

        company_list = []
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

        WhiteListContract = Contract.get_contract(
            'WhiteList',
            os.environ.get('WHITE_LIST_CONTRACT_ADDRESS')
        )

        latest_terms_version = WhiteListContract.functions. \
            latest_terms_version(agent_address).call()
        if latest_terms_version == 0:
            raise DataNotExistsError('eth_address: %s' % eth_address)
        else:
            terms_version = latest_terms_version - 1
            terms = WhiteListContract.functions.terms(agent_address, terms_version).call()
            if not terms[1]:
                raise DataNotExistsError('eth_address: %s' % eth_address)

        for company_info in company_list:
            if to_checksum_address(company_info['address']) == \
                    to_checksum_address(eth_address):
                isExist = True
                terms = {'terms': terms[0]}
                company_info.update(terms)
                self.on_success(res, company_info)
        if not isExist:
            raise DataNotExistsError('eth_address: %s' % eth_address)
