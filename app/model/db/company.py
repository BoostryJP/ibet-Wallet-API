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
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.database import engine
from app.model.db.base import Base


class Company(Base):
    """Issuer Company"""

    __tablename__ = "company"

    # Issuer Address
    address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # Corporate Name
    corporate_name: Mapped[str | None] = mapped_column(Text)
    # RSA Public Key
    rsa_publickey: Mapped[str | None] = mapped_column(String(2000))
    # Homepage URL
    homepage: Mapped[str | None] = mapped_column(Text)

    if engine.name == "mysql":
        # NOTE:MySQLではDatetime型で小数秒桁を指定しない場合、整数秒しか保存されない
        created: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=datetime.utcnow, index=True
        )
    else:
        created: Mapped[datetime | None] = mapped_column(
            DateTime, default=datetime.utcnow, index=True
        )

    def __repr__(self):
        return "<Company address='%s'>" % self.address

    def json(self):
        return {
            "address": self.address,
            "corporate_name": self.corporate_name,
            "rsa_publickey": self.rsa_publickey,
            "homepage": self.homepage,
        }

    FIELDS = {
        "address": str,
        "corporate_name": str,
        "rsa_publickey": str,
        "homepage": str,
    }

    FIELDS.update(Base.FIELDS)
