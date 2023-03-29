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

from sqlalchemy import BigInteger, Column, String

from app.model.db.base import Base


class ExecutableContract(Base):
    __tablename__ = "executable_contract"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    contract_address = Column(String(256), index=True)

    def __repr__(self):
        return "<Listing id='%d' contract_address='%s'>" % (
            self.id,
            self.contract_address,
        )

    FIELDS = {
        "id": int,
        "contract_address": str,
    }

    FIELDS.update(Base.FIELDS)
