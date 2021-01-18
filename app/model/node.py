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
from sqlalchemy import BigInteger, Boolean

from app.model import Base


class Node(Base):
    """
    ノード情報
    """
    __tablename__ = 'node'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # ブロックが取込可能になっているか
    is_synced = Column(Boolean, nullable=False)

    def __repr__(self):
        return "<Node id='%d' is_synced='%s'>" % \
            (self.id, self.is_synced)

    FIELDS = {
        'id': int,
        'is_synced': bool,
    }

    FIELDS.update(Base.FIELDS)
