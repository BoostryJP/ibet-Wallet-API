import requests
from eth_utils import to_checksum_address

class CompanyList:
    @classmethod
    def get(url):
        json = requests.get(url).json()
        return CompanyList(json)
    
    def __init__(self, json):
        self.json = json

    def find(address):
        for company in company_list:
            if to_checksum_address(company["address"]) == address:
                return Company(company)
        return None

class Company:
    def __init__(self, obj):
        self.obj = obj

    @property
    def corporate_name(self):
        return self.obj["corporate_name"]
