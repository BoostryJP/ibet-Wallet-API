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

import asyncio
import hashlib
import json
import sys
import time

from eth_utils import to_checksum_address
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import COMPANY_LIST_SLEEP_INTERVAL, COMPANY_LIST_URL, REQUEST_TIMEOUT
from app.database import BatchAsyncSessionLocal
from app.errors import ServiceUnavailable
from app.model.db import Company
from batch import free_malloc, log

process_name = "INDEXER-COMPANY-LIST"
LOG = log.get_logger(process_name=process_name)


class Processor:
    """Processor for indexing company list"""

    def __init__(self):
        self.company_list_digest = None

    async def process(self):
        LOG.info("Syncing company list")

        # Get from COMPANY_LIST_URL
        try:
            async with AsyncClient() as client:
                _resp = await client.get(COMPANY_LIST_URL, timeout=REQUEST_TIMEOUT)
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
        db_session = BatchAsyncSessionLocal()
        try:
            # Delete all company list from DB
            await db_session.execute(delete(Company))

            # Insert company list
            for i, company in enumerate(company_list_json):
                address = company.get("address", "")
                corporate_name = company.get("corporate_name", "")
                rsa_publickey = company.get("rsa_publickey", "")
                homepage = (
                    company.get("homepage")
                    if company.get("homepage") is not None
                    else ""
                )
                if (
                    not isinstance(address, str)
                    or not isinstance(corporate_name, str)
                    or not isinstance(rsa_publickey, str)
                    or not isinstance(homepage, str)
                ):
                    LOG.notice(f"Invalid type: index={i}")
                    continue
                if address and corporate_name and rsa_publickey:
                    try:
                        address = to_checksum_address(address)
                    except ValueError:
                        LOG.notice(f"Invalid address: index={i} address={address}")
                        continue
                    try:
                        await self.__sink_on_company(
                            db_session=db_session,
                            address=to_checksum_address(address),
                            corporate_name=corporate_name,
                            rsa_publickey=rsa_publickey,
                            homepage=homepage,
                        )
                    except IntegrityError:
                        LOG.notice(f"Duplicate address: index={i} address={address}")
                        continue
                else:
                    LOG.notice(f"Missing required field: index={i}")
                    continue

            await db_session.commit()
            await db_session.close()
        except Exception as e:
            await db_session.rollback()
            await db_session.close()
            raise e
        LOG.info("Sync job has been completed")

    @staticmethod
    async def __sink_on_company(
        db_session: AsyncSession,
        address: str,
        corporate_name: str,
        rsa_publickey: str,
        homepage: str,
    ):
        _company = Company()
        _company.address = address
        _company.corporate_name = corporate_name
        _company.rsa_publickey = rsa_publickey
        _company.homepage = homepage
        await db_session.merge(_company)


async def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()

        try:
            await processor.process()
        except ServiceUnavailable:
            LOG.notice("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception:  # Unexpected errors
            LOG.exception("An exception occurred during event synchronization")

        elapsed_time = time.time() - start_time
        await asyncio.sleep(max(COMPANY_LIST_SLEEP_INTERVAL - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
