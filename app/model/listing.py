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

from datetime import datetime, timedelta, timezone

from sqlalchemy import Column
from sqlalchemy import String, BigInteger, Boolean

from app.model import Base

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


class Listing(Base):
    """
    取扱対象トークン
    """
    __tablename__ = 'listing'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(256), index=True)  # トークンアドレス
    is_public = Column(Boolean)
    max_holding_quantity = Column(BigInteger)  # 最大保有数量
    max_sell_amount = Column(BigInteger)  # 売却価格上限
    owner_address = Column(String(256))  # 発行体アドレス

    def __repr__(self):
        return "<Listing id='%d'>" % self.id

    @staticmethod
    def format_timestamp(_datetime: datetime) -> str:
        """UTCからJSTへ変換
        :param _datetime:
        :return:
        """
        if _datetime is None:
            return ""
        datetime_jp = _datetime.replace(tzinfo=UTC).astimezone(JST)
        return datetime_jp.strftime("%Y/%m/%d %H:%M:%S")

    def json(self):
        return {
            "id": self.id,
            "token_address": self.token_address,
            "is_public": self.is_public,
            "max_holding_quantity": self.max_holding_quantity,
            "max_sell_amount": self.max_sell_amount,
            "owner_address": self.owner_address,
            "created": self.format_timestamp(self.created),
        }

    FIELDS = {
        'id': int,
        'token_address': str,
        'is_public': bool,
        'max_holding_quantity': int,
        'max_sell_amount': int,
        'owner_address': str,
    }

    FIELDS.update(Base.FIELDS)
