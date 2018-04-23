# -*- coding: utf-8 -*-
import json
import requests

from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

# ------------------------------
# 会社情報参照
# ------------------------------
class CompanyInfo(BaseResource):
    '''
    Handle for endpoint: /v1/Company/{eth_address}
    '''
    def on_get(self, req, res, eth_address):
        LOG.info('v1.Company.CompanyInfo')

        company_list = []
        isExist = False

        try:
            company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            raise AppError

        for company_info in company_list:
            if to_checksum_address(company_info['address']) == \
                to_checksum_address(eth_address):
                isExist = True
                self.on_success(res, company_info)
        if isExist == False:
            raise DataNotExistsError('eth_address: %s' % eth_address)
        
