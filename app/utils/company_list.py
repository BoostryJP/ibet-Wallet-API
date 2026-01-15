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
from typing import TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config, log
from app.database import async_engine
from app.model.db import Company as CompanyModel

LOG = log.get_logger()


class Trustee(TypedDict):
    corporate_name: str
    corporate_number: str
    corporate_address: str


class Company(TypedDict):
    address: str
    corporate_name: str
    rsa_publickey: str
    homepage: str
    trustee: Trustee | None


class CompanyList:
    DEFAULT: Company = {
        "address": "",
        "corporate_name": "",
        "rsa_publickey": "",
        "homepage": "",
        "trustee": None,
    }

    @classmethod
    async def get(cls) -> "CompanyList":
        try:
            if config.APP_ENV == "local" or config.COMPANY_LIST_LOCAL_MODE is True:
                company_list: list[Company] = []
                company_list_raw: list[Company] = json.load(
                    open("data/company_list.json", "r")
                )
                for _company in company_list_raw:
                    trustee_raw = _company.get("trustee")
                    trustee_dict: Trustee | None
                    if trustee_raw is not None:
                        trustee_dict = {
                            "corporate_name": trustee_raw.get("corporate_name") or "",
                            "corporate_number": trustee_raw.get("corporate_number")
                            or "",
                            "corporate_address": trustee_raw.get("corporate_address")
                            or "",
                        }
                    else:
                        trustee_dict = None
                    company: Company = {
                        "address": _company.get("address") or "",
                        "corporate_name": _company.get("corporate_name") or "",
                        "rsa_publickey": _company.get("rsa_publickey") or "",
                        "homepage": _company.get("homepage") or "",
                        "trustee": trustee_dict,
                    }
                    company_list.append(company)
            else:
                db_session = AsyncSession(
                    autocommit=False, autoflush=True, bind=async_engine
                )
                try:
                    company_list: list[Company] = []
                    company_models = (
                        await db_session.scalars(
                            select(CompanyModel).order_by(CompanyModel.created)
                        )
                    ).all()
                    for _company in company_models:
                        trustee_dict: Trustee | None
                        if _company.trustee_corporate_name:
                            trustee_dict = {
                                "corporate_name": _company.trustee_corporate_name or "",
                                "corporate_number": _company.trustee_corporate_number
                                or "",
                                "corporate_address": _company.trustee_corporate_address
                                or "",
                            }
                        else:
                            trustee_dict = None
                        company: Company = {
                            "address": _company.address or "",
                            "corporate_name": _company.corporate_name or "",
                            "rsa_publickey": _company.rsa_publickey or "",
                            "homepage": _company.homepage or "",
                            "trustee": trustee_dict,
                        }
                        company_list.append(company)
                finally:
                    await db_session.close()
        except Exception as err:
            company_list = []
            LOG.error(err)
        return cls(company_list)

    def __init__(self, company_list: list[Company]):
        self.company_list = company_list

    def find(self, address: str) -> Company:
        for company in self.company_list:
            if address == company["address"]:
                return company

        return CompanyList.DEFAULT

    def all(self) -> list[Company]:
        return self.company_list

    @staticmethod
    async def get_find(address: str) -> Company:
        try:
            if config.APP_ENV == "local" or config.COMPANY_LIST_LOCAL_MODE is True:
                company_list: list[Company] = json.load(
                    open("data/company_list.json", "r")
                )
                for _company in company_list:
                    if address == _company["address"]:
                        trustee_raw = _company.get("trustee")
                        trustee_dict: Trustee | None
                        if trustee_raw is not None:
                            trustee_dict = {
                                "corporate_name": trustee_raw.get("corporate_name")
                                or "",
                                "corporate_number": trustee_raw.get("corporate_number")
                                or "",
                                "corporate_address": trustee_raw.get(
                                    "corporate_address"
                                )
                                or "",
                            }
                        else:
                            trustee_dict = None
                        company: Company = {
                            "address": _company.get("address") or "",
                            "corporate_name": _company.get("corporate_name") or "",
                            "rsa_publickey": _company.get("rsa_publickey") or "",
                            "homepage": _company.get("homepage") or "",
                            "trustee": trustee_dict,
                        }
                        return company
            else:
                db_session = AsyncSession(
                    autocommit=False, autoflush=True, bind=async_engine
                )
                try:
                    _company = (
                        await db_session.scalars(
                            select(CompanyModel)
                            .where(CompanyModel.address == address)
                            .limit(1)
                        )
                    ).first()
                    if _company is not None:
                        trustee_dict: Trustee | None
                        if _company.trustee_corporate_name:
                            trustee_dict = {
                                "corporate_name": _company.trustee_corporate_name or "",
                                "corporate_number": _company.trustee_corporate_number
                                or "",
                                "corporate_address": _company.trustee_corporate_address
                                or "",
                            }
                        else:
                            trustee_dict = None
                        company: Company = {
                            "address": _company.address or "",
                            "corporate_name": _company.corporate_name or "",
                            "rsa_publickey": _company.rsa_publickey or "",
                            "homepage": _company.homepage or "",
                            "trustee": trustee_dict,
                        }
                        return company
                finally:
                    await db_session.close()
        except Exception as err:
            LOG.error(err)

        return CompanyList.DEFAULT
