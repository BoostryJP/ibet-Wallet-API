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
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app import config, log

LOG = log.get_logger()


def get_engine(uri):
    options = {
        "pool_recycle": 3600,
        "pool_size": 10,
        "pool_timeout": 30,
        "pool_pre_ping": True,
        "max_overflow": 30,
        "echo": config.DB_ECHO,
    }
    return create_engine(uri, **options)


engine = get_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)


def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[Session, Depends(db_session)]


def get_db_schema():
    if config.DATABASE_SCHEMA and engine.name != "mysql":
        return config.DATABASE_SCHEMA
    else:
        return None
