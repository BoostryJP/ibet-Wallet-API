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
import os
import sys
import time

from eth_utils import to_checksum_address
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

import log

from app.config import COMPANY_LIST_SLEEP_INTERVAL, COMPANY_LIST_URL, REQUEST_TIMEOUT
from app.database import batch_async_engine
from app.errors import ServiceUnavailable
from app.model.db import Company

process_name = "INDEXER-COMPANY-LIST"
LOG = log.get_logger(process_name=process_name)


class Processor:
    """Processor for indexing company list"""

    async def process(self):
        LOG.info("Syncing company list")

        # Get from COMPANY_LIST_URL
        try:
            async with AsyncClient() as client:
                req = await client.get(COMPANY_LIST_URL, timeout=REQUEST_TIMEOUT)
            if req.status_code != 200:
                raise Exception(f"status code={req.status_code}")
            company_list_json = req.json()
        except Exception as e:
            LOG.exception(f"Failed to get company list: {e}")
            return

        db_session = AsyncSession(
            autocommit=False, autoflush=True, bind=batch_async_engine
        )
        try:
            # Upsert company list
            updated_company_dict: dict[str, True] = {}
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
                    LOG.warning(f"type error: index={i}")
                    continue
                if address and corporate_name and rsa_publickey:
                    try:
                        address = to_checksum_address(address)
                    except ValueError:
                        LOG.warning(
                            f"invalid address error: index={i} address={address}"
                        )
                        continue
                    try:
                        has_already_updated = updated_company_dict.get(address, False)
                        if has_already_updated:
                            LOG.warning(
                                f"duplicate address error: index={i} address={address}"
                            )
                            continue
                        await self.__sink_on_company(
                            db_session=db_session,
                            address=to_checksum_address(address),
                            corporate_name=corporate_name,
                            rsa_publickey=rsa_publickey,
                            homepage=homepage,
                        )
                    except IntegrityError:
                        LOG.warning(
                            f"duplicate address error: index={i} address={address}"
                        )
                        continue
                else:
                    LOG.warning(f"required error: index={i}")
                    continue
                updated_company_dict[address] = True

            # Delete company list from DB
            company_list_db = (await db_session.scalars(select(Company))).all()
            for company in company_list_db:
                is_updated = updated_company_dict.get(company.address, False)
                if not is_updated:
                    await db_session.delete(company)

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
            LOG.warning("An external service was unavailable")
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:  # Unexpected errors
            LOG.exception("An exception occurred during event synchronization")

        elapsed_time = time.time() - start_time
        await asyncio.sleep(max(COMPANY_LIST_SLEEP_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(1)
