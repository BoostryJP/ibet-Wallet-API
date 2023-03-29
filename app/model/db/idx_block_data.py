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
from sqlalchemy import JSON, BigInteger, Column, Integer, String, Text

from app.model.db.base import Base


class IDXBlockData(Base):
    """Block data (INDEX)"""

    __tablename__ = "block_data"

    # Header data
    number = Column(BigInteger, primary_key=True, autoincrement=False)
    parent_hash = Column(String(66), nullable=False)
    sha3_uncles = Column(String(66))
    miner = Column(String(42))
    state_root = Column(String(66))
    transactions_root = Column(String(66))
    receipts_root = Column(String(66))
    logs_bloom = Column(String(514))
    difficulty = Column(BigInteger)
    gas_limit = Column(Integer)
    gas_used = Column(Integer)
    timestamp = Column(Integer, nullable=False, index=True)
    proof_of_authority_data = Column(Text)
    mix_hash = Column(String(66))
    nonce = Column(String(18))

    # Other data
    hash = Column(String(66), nullable=False, index=True)
    size = Column(Integer)
    transactions = Column(JSON)

    FIELDS = {
        "number": int,
        "parent_hash": str,
        "sha3_uncles": str,
        "miner": str,
        "state_root": str,
        "transactions_root": str,
        "receipts_root": str,
        "logs_bloom": str,
        "difficulty": int,
        "gas_limit": int,
        "gas_used": int,
        "timestamp": int,
        "proof_of_authority_data": str,
        "mix_hash": str,
        "nonce": str,
        "hash": str,
        "size": int,
        "transactions": list[str],
    }
    FIELDS.update(Base.FIELDS)


class IDXBlockDataBlockNumber(Base):
    """Synchronized blockNumber of IDXBlockData"""

    __tablename__ = "idx_block_data_block_number"

    # Chain id
    chain_id = Column(String(10), primary_key=True)
    # Latest blockNumber
    latest_block_number = Column(BigInteger)

    FIELDS = {
        "latest_block_number": int,
    }
    FIELDS.update(Base.FIELDS)
