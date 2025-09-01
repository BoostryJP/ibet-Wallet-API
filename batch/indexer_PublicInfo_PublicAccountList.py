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
from eth_utils import to_checksum_address
from sqlalchemy import delete
from sqlalchemy.engine.create import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.session import Session
from urllib3 import Retry

from app.config import (
    DATABASE_URL,
    PUBLIC_ACCOUNT_LIST_SLEEP_INTERVAL,
    PUBLIC_ACCOUNT_LIST_URL,
    REQUEST_TIMEOUT,
)
from app.errors import ServiceUnavailable
from app.model.db import PublicAccountList
from batch import free_malloc, log

process_name = "INDEXER-PUBLIC-INFO-PUBLIC-ACCOUNT"
LOG = log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing public account list"""

    def __init__(self):
        self.account_list_digest = None

    def process(self):
        LOG.info("Syncing public account list")

        # Get data from PUBLIC_ACCOUNT_LIST_URL
        try:
            _resp = requests.get(
                PUBLIC_ACCOUNT_LIST_URL,
                timeout=REQUEST_TIMEOUT,
                retry=Retry(total=3, allowed_methods=["GET"]),
            )
            if _resp.status_code != 200:
                raise Exception(f"status code={_resp.status_code}")
            account_list_json = _resp.json()
        except Exception:
            LOG.exception("Failed to get public account list")
            return

        # Check the difference from the previous cycle
        _resp_digest = hashlib.sha256(
            json.dumps(account_list_json).encode()
        ).hexdigest()
        if _resp_digest == self.account_list_digest:
            LOG.info("Skip: There are no differences from the previous cycle")
            return
        else:
            self.account_list_digest = _resp_digest

        # Update DB data
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            # Delete all account list from DB
            db_session.execute(delete(PublicAccountList))

            # Insert account list
            for i, _account in enumerate(account_list_json):
                key_manager = _account.get("key_manager", None)
                key_manager_name = _account.get("key_manager_name", None)
                account_type = _account.get("type", None)
                account_address = _account.get("account_address", None)

                if (
                    not isinstance(key_manager, str)
                    or not isinstance(key_manager_name, str)
                    or not isinstance(account_type, int)
                    or not isinstance(account_address, str)
                ):
                    LOG.notice(
                        f"Invalid type: key_manager={key_manager}, key_manager_name={key_manager_name}, type={account_type}, account_address={account_address}"
                    )
                    continue
                try:
                    account_address = to_checksum_address(account_address)
                except ValueError:
                    LOG.notice(
                        f"Invalid address: index={i} account_address={account_address}"
                    )
                    continue
                self.__sink_on_account_list(
                    db_session=db_session,
                    key_manager=key_manager,
                    key_manager_name=key_manager_name,
                    account_type=account_type,
                    account_address=account_address,
                )

            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

        LOG.info("Sync job has been completed")

    @staticmethod
    def __sink_on_account_list(
        db_session: Session,
        key_manager: str,
        key_manager_name: str,
        account_type: int,
        account_address: str,
    ):
        _account_list = PublicAccountList()
        _account_list.key_manager = key_manager
        _account_list.key_manager_name = key_manager_name
        _account_list.account_type = account_type
        _account_list.account_address = account_address
        db_session.merge(_account_list)


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
        time.sleep(max(PUBLIC_ACCOUNT_LIST_SLEEP_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
