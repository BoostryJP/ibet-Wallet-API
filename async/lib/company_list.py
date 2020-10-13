# -*- coding: utf-8 -*-
import json
import requests
from eth_utils import to_checksum_address

from app import config
from app import log
LOG = log.get_logger()


class CompanyListFactory:
    def __init__(self, url):
        self.url = url

    def get(self):
        return CompanyList.get(self.url)


class CompanyList:
    @classmethod
    def get(self, url):
        try:
            if config.APP_ENV == 'local' or config.COMPANY_LIST_LOCAL_MODE is True:
                resp_json = json.load(open('data/company_list.json', 'r'))
            else:
                resp_json = requests.get(url, timeout=config.REQUEST_TIMEOUT).json()
        except Exception as err:
            resp_json = {}
            LOG.error(err)
        return CompanyList(resp_json)

    def __init__(self, list_json):
        self.json = list_json

    def find(self, address):
        company_default = {
            "address": "",
            "corporate_name": "",
            "rsa_publickey": "",
            "homepage": ""
        }

        for company in self.json:
            if "address" in company:
                if to_checksum_address(company["address"]) == address:
                    return Company(company)

        return Company(company_default)


class Company:
    def __init__(self, obj):
        self.obj = obj

    @property
    def corporate_name(self):
        return self.obj["corporate_name"]
