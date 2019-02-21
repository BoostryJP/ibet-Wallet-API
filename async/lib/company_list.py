import requests
from eth_utils import to_checksum_address

import logging
from app import log
logging.getLogger("urllib3").setLevel(logging.WARNING)
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
            json = requests.get(url, timeout=(3.0, 7.5)).json()
        except Exception as err:
            json = '{}'
            LOG.error(err)
        return CompanyList(json)

    def __init__(self, json):
        self.json = json

    def find(self, address):
        company_default = {
            "address": "",
            "corporate_name": "",
            "enode": "",
            "ip_address": "",
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
