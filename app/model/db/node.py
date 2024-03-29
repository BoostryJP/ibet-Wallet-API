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

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db.base import Base


class Node(Base):
    """
    Ethereum Node Information
    """

    __tablename__ = "node"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # endpoint uri(http[s]://domain:port)
    endpoint_uri: Mapped[str | None] = mapped_column(String(267))
    # connect priority(top priority is lower number)
    priority: Mapped[int | None] = mapped_column(Integer)
    # node synchronized status
    is_synced: Mapped[bool] = mapped_column(Boolean, nullable=False)

    def __repr__(self):
        return "<Node id='%d' is_synced='%s'>" % (self.id, self.is_synced)

    FIELDS = {
        "id": int,
        "endpoint_uri": str,
        "priority": int,
        "is_synced": bool,
    }

    FIELDS.update(Base.FIELDS)
