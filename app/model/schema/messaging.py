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
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, Json, conlist, constr

############################
# REQUEST
############################


class SendMailRequest(BaseModel):
    to_emails: conlist(EmailStr, min_items=1, max_items=100, unique_items=True)
    subject: constr(max_length=100) = Field(..., description="Mail subject")
    text_content: Optional[str] = Field("", description="Plain text mail content")
    html_content: Optional[str] = Field("", description="HTML mail content")


class SendChatWebhookRequest(BaseModel):
    message: Json = Field(..., description="Message body")
