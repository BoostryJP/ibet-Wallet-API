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

from typing import Literal

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.model.db.base import Base


class TokenList(Base):
    """Token List"""

    __tablename__ = "token_list"

    # Token Address
    token_address: Mapped[str] = mapped_column(String(42), primary_key=True)
    # Token Template
    token_template: Mapped[Literal["ibetBond", "ibetShare"]] = mapped_column(
        String(50), nullable=False
    )
    # Key Manager
    key_manager: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    # Product Type
    product_type: Mapped[Literal[1, 2, 3, 4, 5]] = mapped_column(
        Integer, nullable=False
    )

    def json(self):
        return {
            "token_address": self.token_address,
            "token_template": self.token_template,
            "key_manager": self.key_manager,
            "product_type": self.product_type,
        }
