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
import os
import sys
import time

from eth_utils import to_checksum_address
import requests
from sqlalchemy import create_engine
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError
)
from sqlalchemy.orm import Session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app.config import (
    DATABASE_URL,
    COMPANY_LIST_URL,
    COMPANY_LIST_SLEEP_INTERVAL,
    REQUEST_TIMEOUT
)
from app.errors import ServiceUnavailable
from app.model.db import Company
import log

process_name = "INDEXER-COMPANY-LIST"
LOG = log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False)


class Processor:
    """Processor for indexing company list"""

    def process(self):
        LOG.info("syncing company list")

        # Get from COMPANY_LIST_URL
        try:
            req = requests.get(COMPANY_LIST_URL, timeout=REQUEST_TIMEOUT)
            if req.status_code != 200:
                raise Exception(f"status code={req.status_code}")
            company_list_json = req.json()
        except Exception as e:
            LOG.exception(f"Failed to get company list: {e}")
            return

        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            # Delete all company list from DB
            _company_list = db_session.query(Company).all()
            for _company in _company_list:
                db_session.delete(_company)

            # Insert company list
            for i, company in enumerate(company_list_json):
                address = company.get("address", "")
                corporate_name = company.get("corporate_name", "")
                rsa_publickey = company.get("rsa_publickey", "")
                homepage = company.get("homepage") if company.get("homepage") is not None else ""
                if not isinstance(address, str) or \
                        not isinstance(corporate_name, str) or \
                        not isinstance(rsa_publickey, str) or \
                        not isinstance(homepage, str):
                    LOG.warning(f"type error: index={i}")
                    continue
                if address and corporate_name and rsa_publickey:
                    try:
                        address = to_checksum_address(address)
                    except ValueError:
                        LOG.warning(f"invalid address error: index={i} address={address}")
                        continue
                    try:
                        self.__sink_on_company(
                            db_session=db_session,
                            address=to_checksum_address(address),
                            corporate_name=corporate_name,
                            rsa_publickey=rsa_publickey,
                            homepage=homepage,
                        )
                    except IntegrityError:
                        LOG.warning(f"duplicate address error: index={i} address={address}")
                        continue
                else:
                    LOG.warning(f"required error: index={i}")
                    continue
            db_session.commit()
            db_session.close()
        except Exception as e:
            db_session.rollback()
            db_session.close()
            raise e

    @staticmethod
    def __sink_on_company(db_session: Session,
                          address: str,
                          corporate_name: str,
                          rsa_publickey: str,
                          homepage: str):
        _company = db_session.query(Company).filter(Company.address == address).first()
        if _company is None:
            _company = Company()
            _company.address = address
            _company.corporate_name = corporate_name
            _company.rsa_publickey = rsa_publickey
            _company.homepage = homepage
            db_session.add(_company)


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()

        try:
            processor.process()
            LOG.debug("Processed")
        except ServiceUnavailable:
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:  # Unexpected errors
            LOG.exception(ex)

        elapsed_time = time.time() - start_time
        time.sleep(max(COMPANY_LIST_SLEEP_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()
