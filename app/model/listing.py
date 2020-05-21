# -*- coding: utf-8 -*-
from sqlalchemy import Column
from sqlalchemy import String, BigInteger

from app.model import Base


class Listing(Base):
    """
    取扱対象トークン
    """
    __tablename__ = 'listing'
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    token_address = Column(String(256), index=True)  # トークンアドレス
    max_holding_quantity = Column(BigInteger)  # 最大保有数量
    max_sell_amount = Column(BigInteger)  # 売却価格上限
    owner_address = Column(String(256), index=True)  # 発行体アドレス

    def __repr__(self):
        return "<Listing id='%d'>" % self.id

    FIELDS = {
        'id': int,
        'token_address': str,
        'token_template': str,
        'max_holding_quantity': int,
        'max_sell_amount': int,
        'owner_address': str,
    }

    FIELDS.update(Base.FIELDS)
