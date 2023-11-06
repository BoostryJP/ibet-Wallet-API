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

SPDX-License
"""
import json

from fastapi import APIRouter

from app import log
from app.database import DBSession
from app.errors import InvalidParameterError
from app.model.db import ChatWebhook, Mail
from app.model.schema import SendChatWebhookRequest, SendMailRequest
from app.model.schema.base import SuccessResponse
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="", tags=["messaging"])


@router.post(
    "/Mail",
    summary="Send Email",
    operation_id="SendEmail",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError),
)
def send_mail(session: DBSession, data: SendMailRequest):
    """
    Sends Email.
    """
    for to_email in data.to_emails:
        mail = Mail()
        mail.to_email = to_email
        mail.subject = data.subject
        mail.text_content = data.text_content
        mail.html_content = data.html_content
        if data.file_content:
            mail.file_content = data.file_content
        if data.file_name:
            mail.file_name = data.file_name
        session.add(mail)

    session.commit()

    return json_response(SuccessResponse.default())


@router.post(
    "/Chat/Webhook",
    summary="Send chat messages using incoming webhooks",
    operation_id="SendChatWebhook",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError),
)
def send_chat_webhook(session: DBSession, data: SendChatWebhookRequest):
    """
    Sends Chat Webhook.
    """
    hook = ChatWebhook()
    hook.message = json.dumps(data.message)
    session.add(hook)
    session.commit()

    return json_response(SuccessResponse.default())
