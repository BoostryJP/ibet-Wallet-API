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

from sqlalchemy import CheckConstraint, DateTime, Index, String, Text
from sqlalchemy.dialects.mysql import DATETIME as MySQLDATETIME
from sqlalchemy.orm import Mapped, mapped_column

from app.database import engine
from app.model.db.base import Base, naive_utcnow


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
    # Trustee Corporate Name
    trustee_corporate_name: Mapped[str | None] = mapped_column(String(30))
    # Trustee Corporate Number
    trustee_corporate_number: Mapped[str | None] = mapped_column(String(20))
    # Trustee Corporate Address
    trustee_corporate_address: Mapped[str | None] = mapped_column(String(60))

    if engine.name == "mysql":
        # NOTE:MySQLではDatetime型で小数秒桁を指定しない場合、整数秒しか保存されない
        created: Mapped[datetime | None] = mapped_column(
            MySQLDATETIME(fsp=6), default=naive_utcnow, index=True
        )
    else:
        created: Mapped[datetime | None] = mapped_column(
            DateTime, default=naive_utcnow, index=True
        )
    __table_args__ = (
        CheckConstraint(
            "((trustee_corporate_name IS NULL AND trustee_corporate_number IS NULL AND trustee_corporate_address IS NULL) "
            "OR (trustee_corporate_name IS NOT NULL AND trustee_corporate_number IS NOT NULL AND trustee_corporate_address IS NOT NULL))",
            name="ck_company_trustee_fields_complete",
        ),
        # Covering Index
        Index(
            "ix_company_covering",
            "created",
            "address",
            "corporate_name",
            "rsa_publickey",
            "homepage",
            "modified",
            mysql_length={"corporate_name": 100, "rsa_publickey": 255, "homepage": 255},
        ),
    )

    def __repr__(self):
        return "<Company address='%s'>" % self.address

    def json(self):
        return {
            "address": self.address,
            "corporate_name": self.corporate_name,
            "rsa_publickey": self.rsa_publickey,
            "homepage": self.homepage,
            "trustee": {
                "corporate_name": self.trustee_corporate_name,
                "corporate_number": self.trustee_corporate_number,
                "corporate_address": self.trustee_corporate_address,
            }
            if self.trustee_corporate_name
            else None,
        }
