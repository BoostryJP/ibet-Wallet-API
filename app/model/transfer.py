# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, BigInteger
from datetime import datetime, timedelta, timezone

from app.model import Base

UTC = timezone(timedelta(hours=0), "UTC")
JST = timezone(timedelta(hours=+9), "JST")


class Transfer(Base):
    """
    トークン移転（Event）
    """
    __tablename__ = 'transfer'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_hash = Column(String(66), index=True)
    token_address = Column(String(42), index=True)
    from_address = Column(String(42))
    to_address = Column(String(42))
    value = Column(BigInteger)

    def __repr__(self):
        return "<Transfer(transaction_hash='%s', token_address='%s', from_address='%s', to_address='%s', value='%d')>" % \
               (self.transaction_hash, self.token_address, self.from_address, self.to_address, self.value)

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
            "transaction_hash": self.transaction_hash,
            "token_address": self.token_address,
            "from_address": self.from_address,
            "to_address": self.to_address,
            "value": self.value,
            "created": self.format_timestamp(self.created),
        }

    FIELDS = {
        'id': int,
        'transaction_hash': str,
        'token_address': str,
        'from_address': str,
        'to_address': str,
        'value': int,
    }

    FIELDS.update(Base.FIELDS)
