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
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text
)

from app.model.db import Base


class Mail(Base):
    """
    Email message
    """
    __tablename__ = 'mail'

    # unique id
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    # to email address
    to_email = Column(String(256), nullable=False)
    # subject
    subject = Column(String(100), nullable=False)
    # plain text mail content
    text_content = Column(Text, nullable=False)
    # html mail content
    html_content = Column(Text, nullable=False)

    FIELDS = {
        "id": int,
        "to_email": str,
        "subject": str,
        "text_content": str,
        "html_content": str
    }
    FIELDS.update(Base.FIELDS)
