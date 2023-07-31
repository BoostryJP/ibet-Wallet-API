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
import re
import string
from typing import Optional, Self, Set

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    Json,
    StringConstraints,
    field_validator,
    model_validator,
)
from typing_extensions import Annotated

############################
# COMMON
############################


def _get_unprintable_ascii_chars() -> list[str]:
    return [chr(c) for c in range(128) if chr(c) not in string.printable]


# ASCII control characters
UNPRINTABLE_ASCII_CHARS = tuple(_get_unprintable_ascii_chars())
# Not allowed characters for path
INVALID_PATH_CHARS = "".join(UNPRINTABLE_ASCII_CHARS)
# Not allowed characters for file name
INVALID_FILENAME_CHARS = INVALID_PATH_CHARS + "/"
# Not allowed characters for path on Windows OS
INVALID_WIN_PATH_CHARS = INVALID_PATH_CHARS + ':*?"<>|\t\n\r\x0b\x0c'
# Not allowed characters for file name on Windows OS
INVALID_WIN_FILENAME_CHARS = INVALID_FILENAME_CHARS + INVALID_WIN_PATH_CHARS + "\\"
# Regex object for file name validation
RE_INVALID_WIN_FILENAME = re.compile(
    f"[{re.escape(INVALID_WIN_FILENAME_CHARS):s}]", re.UNICODE
)

############################
# REQUEST
############################


class SendMailRequest(BaseModel):
    to_emails: Set[EmailStr] = Field(min_length=1, max_length=100)
    subject: str = Field(..., description="Mail subject", max_length=100)
    text_content: Optional[str] = Field("", description="Plain text mail content")
    html_content: Optional[str] = Field("", description="HTML mail content")
    file_name: Optional[str] = Field(
        default=None, description="File name", min_length=1, max_length=255
    )
    file_content: Optional[bytes] = Field(
        default=None, description="File content(Base64 encoded)", min_length=1
    )

    @field_validator("file_name")
    @classmethod
    def is_valid_file_name(cls, v):
        if v:
            match = RE_INVALID_WIN_FILENAME.search(v)
            if match:
                raise ValueError("File name has invalid character.")
        return v

    @model_validator(mode="after")
    @classmethod
    def validate_file(cls, values: Self):
        if (values.file_content and not values.file_name) or (
            not values.file_content and values.file_name
        ):
            raise ValueError("File content should be posted with name.")
        return values


class SendChatWebhookRequest(BaseModel):
    message: Json = Field(..., description="Message body")
