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

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db.base import Base


class IDXTokenListRegister(Base):
    """Token List Register Event (INDEX)"""

    __tablename__ = "token_list_register"

    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # Token Template
    token_template: Mapped[str | None] = mapped_column(String(40))
    # Owner Address
    owner_address: Mapped[str | None] = mapped_column(String(42), index=True)

    FIELDS = {
        "token_address": str,
        "token_template": str,
        "owner_address": str,
    }

    FIELDS.update(Base.FIELDS)


class IDXTokenListBlockNumber(Base):
    """Synchronized blockNumber of IDXTokenList"""

    __tablename__ = "idx_token_list_block_number"

    # target address
    contract_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # latest blockNumber
    latest_block_number: Mapped[int | None] = mapped_column(BigInteger)

    FIELDS = {
        "contract_address": str,
        "latest_block_number": int,
    }

    FIELDS.update(Base.FIELDS)
