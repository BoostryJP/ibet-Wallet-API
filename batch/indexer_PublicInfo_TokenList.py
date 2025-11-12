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
from typing import Literal

import requests
from pydantic import ValidationError
from requests.adapters import HTTPAdapter
from sqlalchemy import delete
from sqlalchemy.engine.create import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.session import Session
from urllib3 import Retry

from app.config import (
    DATABASE_URL,
    REQUEST_TIMEOUT,
    TOKEN_LIST_SLEEP_INTERVAL,
    TOKEN_LIST_URL,
)
from app.errors import ServiceUnavailable
from app.model.db import TokenList
from app.model.type.token_list import TokenListItem
from batch import free_malloc, log

process_name = "INDEXER-PUBLIC-INFO-TOKEN-LIST"
LOG = log.get_logger(process_name=process_name)

db_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    """Processor for indexing token list"""

    def __init__(self):
        self.token_list_digest = None

    def process(self):
        LOG.info("Syncing token list")

        # Get from TOKEN_LIST_URL
        try:
            if TOKEN_LIST_URL is None:
                LOG.warning("TOKEN_LIST_URL is not set")
                return
            with requests.Session() as session:
                adapter = HTTPAdapter(max_retries=Retry(3, allowed_methods=["GET"]))
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                _resp = session.get(
                    url=TOKEN_LIST_URL,
                    timeout=REQUEST_TIMEOUT,
                )
                if _resp.status_code != 200:
                    raise Exception(f"status code={_resp.status_code}")
                token_list_json = _resp.json()
        except Exception:
            LOG.exception("Failed to get token list")
            return

        # Check the difference from the previous cycle
        _resp_digest = hashlib.sha256(json.dumps(token_list_json).encode()).hexdigest()
        if _resp_digest == self.token_list_digest:
            LOG.info("Skip: There are no differences from the previous cycle")
            return
        else:
            self.token_list_digest = _resp_digest

        # Update DB data
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            # Delete all token list from DB
            db_session.execute(delete(TokenList))

            # Insert token list
            for i, token in enumerate(token_list_json):
                try:
                    token_list_item = TokenListItem.model_validate(token)
                except (ValidationError, ValueError):
                    LOG.notice(f"Invalid token data: index={i} token={token}")
                    continue

                token_address = token_list_item.token_address
                token_template = token_list_item.token_template
                key_manager = token_list_item.key_manager
                product_type = token_list_item.product_type

                self.__sink_on_token_list(
                    db_session=db_session,
                    token_address=token_address,
                    token_template=token_template,
                    key_manager=key_manager,
                    product_type=product_type,
                )

            db_session.commit()
        except Exception as e:
            db_session.rollback()
            raise e
        finally:
            db_session.close()

        LOG.info("Sync job has been completed")

    @staticmethod
    def __sink_on_token_list(
        db_session: Session,
        token_address: str,
        token_template: Literal[
            "ibetBond", "ibetShare", "ibetMembership", "ibetCoupon"
        ],
        key_manager: list[str],
        product_type: int,
    ):
        _token_list = TokenList()
        _token_list.token_address = token_address
        _token_list.token_template = token_template
        _token_list.key_manager = key_manager
        _token_list.product_type = product_type
        db_session.merge(_token_list)


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
        time.sleep(max(TOKEN_LIST_SLEEP_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
