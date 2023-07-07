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
from typing import Optional

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    Json,
    conbytes,
    conlist,
    constr,
    root_validator,
    validator,
)

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
    to_emails: conlist(EmailStr, min_items=1, max_items=100, unique_items=True)
    subject: constr(max_length=100) = Field(..., description="Mail subject")
    text_content: Optional[str] = Field("", description="Plain text mail content")
    html_content: Optional[str] = Field("", description="HTML mail content")
    file_name: Optional[constr(min_length=1, max_length=255)] = Field(
        default=None, description="File name"
    )
    file_content: Optional[conbytes(min_length=1)] = Field(
        default=None, description="File content(Base64 encoded)"
    )

    @validator("file_name")
    def is_valid_file_name(cls, v):
        if v:
            match = RE_INVALID_WIN_FILENAME.search(v)
            if match:
                raise ValueError("File name has invalid character.")
        return v

    @root_validator
    def validate_file(cls, values):
        if (values.get("file_content") and not values.get("file_name")) or (
            not values.get("file_content") and values.get("file_name")
        ):
            raise ValueError("File content should be posted with name.")
        return values


class SendChatWebhookRequest(BaseModel):
    message: Json = Field(..., description="Message body")
