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
from sqlalchemy import Column
from sqlalchemy import (
    String,
    Text
)

from app.model.db import Base


class Company(Base):
    """Issuer Company"""
    __tablename__ = "company"

    # Issuer Address
    address = Column(String(42), primary_key=True)
    # Corporate Name
    corporate_name = Column(Text)
    # RSA Public Key
    rsa_publickey = Column(String(2000))
    # Homepage URL
    homepage = Column(Text)

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
        'address': str,
        'corporate_name': str,
        'rsa_publickey': str,
        'homepage': str,
    }

    FIELDS.update(Base.FIELDS)
