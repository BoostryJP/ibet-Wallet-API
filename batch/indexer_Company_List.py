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

import hashlib
import json
import sys
import time

import requests
from pydantic import ValidationError
from requests.adapters import HTTPAdapter
from sqlalchemy import delete
from sqlalchemy.engine.create import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.session import Session
from urllib3 import Retry

from app.config import (
    COMPANY_LIST_SLEEP_INTERVAL,
    COMPANY_LIST_URL,
    DATABASE_URL,
    REQUEST_TIMEOUT,
)
from app.errors import ServiceUnavailable
from app.model.db import Company
from app.model.type import CompanyListItem
from batch import free_malloc, log

process_name = "INDEXER-COMPANY-LIST"
LOG = log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing company list"""

    def __init__(self):
        self.company_list_digest = None

    def process(self):
        LOG.info("Syncing company list")

        # Get from COMPANY_LIST_URL
        if COMPANY_LIST_URL is None:
            LOG.warning("COMPANY_LIST_URL is not set")
            return
        try:
            with requests.Session() as session:
                adapter = HTTPAdapter(max_retries=Retry(3, allowed_methods=["GET"]))
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                _resp = session.get(
                    url=COMPANY_LIST_URL,
                    timeout=REQUEST_TIMEOUT,
                )
                if _resp.status_code != 200:
                    raise Exception(f"status code={_resp.status_code}")
                company_list_json = _resp.json()
        except Exception:
            LOG.exception("Failed to get company list")
            return

        # Check the difference from the previous cycle
        _resp_digest = hashlib.sha256(
            json.dumps(company_list_json).encode()
        ).hexdigest()
        if _resp_digest == self.company_list_digest:
            LOG.info("Skip: There are no differences from the previous cycle")
            return
        else:
            self.company_list_digest = _resp_digest

        # Update DB data
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            # Delete all company list from DB
            db_session.execute(delete(Company))

            # Insert company list
            for i, company in enumerate(company_list_json):
                try:
                    company_list_item = CompanyListItem.model_validate(company)  # type: ignore[arg-type]
                except (ValidationError, ValueError):
                    LOG.notice(f"Invalid company data: index={i} company={company}")
                    continue

                if (
                    company_list_item.address
                    and company_list_item.corporate_name
                    and company_list_item.rsa_publickey
                ):
                    self.__sink_on_company(
                        db_session=db_session,
                        company_list_item=company_list_item,
                    )
                else:
                    LOG.notice(f"Missing required field: index={i}")
                    continue

            db_session.commit()
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
        LOG.info("Sync job has been completed")

    @staticmethod
    def __sink_on_company(
        db_session: Session,
        company_list_item: CompanyListItem,
    ):
        _company = Company()
        _company.address = company_list_item.address
        _company.corporate_name = company_list_item.corporate_name
        _company.rsa_publickey = company_list_item.rsa_publickey
        _company.homepage = company_list_item.homepage
        if company_list_item.trustee:
            _company.trustee_corporate_name = company_list_item.trustee.corporate_name
            _company.trustee_corporate_number = (
                company_list_item.trustee.corporate_number
            )
            _company.trustee_corporate_address = (
                company_list_item.trustee.corporate_address
            )
        db_session.merge(_company)


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()

        try:
            processor.process()
        except ServiceUnavailable:
            LOG.notice("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:  # Unexpected errors
            LOG.exception("An exception occurred during processing")

        elapsed_time = time.time() - start_time
        time.sleep(max(COMPANY_LIST_SLEEP_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
