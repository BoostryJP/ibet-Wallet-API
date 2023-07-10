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
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, log
from app.database import get_engine
from app.model.db import Company as CompanyModel

engine = get_engine(config.DATABASE_URL)

LOG = log.get_logger()


class CompanyList:
    DEFAULT = {"address": "", "corporate_name": "", "rsa_publickey": "", "homepage": ""}

    @classmethod
    def get(cls):
        try:
            if config.APP_ENV == "local" or config.COMPANY_LIST_LOCAL_MODE is True:
                company_list = []
                _company_list = json.load(open("data/company_list.json", "r"))
                for _company in _company_list:
                    company_list.append(Company(_company))
            else:
                db_session = Session(autocommit=False, autoflush=True, bind=engine)
                try:
                    company_list = []
                    _company_list = (
                        db_session.execute(
                            select(CompanyModel).order_by(CompanyModel.created)
                        )
                        .scalars()
                        .all()
                    )
                    for _company in _company_list:
                        company_list.append(Company(_company.json()))
                finally:
                    db_session.close()
        except Exception as err:
            company_list = []
            LOG.error(err)
        return cls(company_list)

    def __init__(self, company_list):
        self.company_list = company_list

    def find(self, address):
        for company in self.company_list:
            if address == company.address:
                return company

        return Company(CompanyList.DEFAULT)

    def all(self):
        return self.company_list

    @staticmethod
    def get_find(address):
        try:
            if config.APP_ENV == "local" or config.COMPANY_LIST_LOCAL_MODE is True:
                company_list = json.load(open("data/company_list.json", "r"))
                for _company in company_list:
                    if address == _company["address"]:
                        return Company(_company)
            else:
                db_session = Session(autocommit=False, autoflush=True, bind=engine)
                try:
                    _company = (
                        db_session.execute(
                            select(CompanyModel).where(CompanyModel.address == address)
                        )
                        .scalars()
                        .first()
                    )
                    if _company is not None:
                        return Company(_company.json())
                finally:
                    db_session.close()
        except Exception as err:
            LOG.error(err)

        return Company(CompanyList.DEFAULT)


class Company:
    def __init__(self, obj):
        self.obj = obj

    @property
    def address(self):
        return self.obj.get("address")

    @property
    def corporate_name(self):
        return self.obj.get("corporate_name")

    @property
    def rsa_publickey(self):
        return self.obj.get("rsa_publickey")

    @property
    def homepage(self):
        return self.obj.get("homepage")

    def json(self):
        return {
            "address": self.obj.get("address") or "",
            "corporate_name": self.obj.get("corporate_name") or "",
            "rsa_publickey": self.obj.get("rsa_publickey") or "",
            "homepage": self.obj.get("homepage") or "",
        }

    def __getitem__(self, key: str):
        return self.obj[key]
