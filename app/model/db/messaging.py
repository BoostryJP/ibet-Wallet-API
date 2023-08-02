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
from sqlalchemy import BigInteger, LargeBinary, String, Text
from sqlalchemy.dialects.mysql import LONGBLOB
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db.base import Base


class Mail(Base):
    """
    Email message
    """

    __tablename__ = "mail"

    # unique id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # to email address
    to_email: Mapped[str] = mapped_column(String(256), nullable=False)
    # subject
    subject: Mapped[str] = mapped_column(String(100), nullable=False)
    # plain text mail content
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    # html mail content
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    # file name
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # file content
    file_content: Mapped[str | None] = mapped_column(
        LargeBinary().with_variant(LONGBLOB, "mysql"), nullable=True
    )

    FIELDS = {
        "id": int,
        "to_email": str,
        "subject": str,
        "text_content": str,
        "html_content": str,
        "file_name": str,
        "file_content": bytes,
    }
    FIELDS.update(Base.FIELDS)


class ChatWebhook(Base):
    """
    Chat webhook message
    """

    __tablename__ = "chat_webhook"

    # unique id
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # html mail content
    message: Mapped[str] = mapped_column(Text, nullable=False)

    FIELDS = {
        "id": int,
        "message": str,
    }
    FIELDS.update(Base.FIELDS)
