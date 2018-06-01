import requests
from eth_utils import to_checksum_address

class CompanyListFactory:
    def __init__(self, url):
        self.url = url

    def get(self):
        return CompanyList.get(self.url)

class CompanyList:
    @classmethod
    def get(self, url):
        json = requests.get(url).json()
        return CompanyList(json)
    
    def __init__(self, json):
        self.json = json

    def find(self, address):
        for company in self.json:
            if to_checksum_address(company["address"]) == address:
                return Company(company)
        return None

class Company:
    def __init__(self, obj):
        self.obj = obj

    @property
    def corporate_name(self):
        return self.obj["corporate_name"]
