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
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Sequence

from fastapi import APIRouter, Query
from sqlalchemy import func, select, update

from app import log
from app.database import DBAsyncSession
from app.errors import DataNotExistsError, InvalidParameterError
from app.model.db import ChatWebhook, Mail, MailStatus
from app.model.schema import (
    ListMailsQuery,
    ListMailsResponse,
    MailData,
    ResendMailsRequest,
    SendChatWebhookRequest,
    SendMailRequest,
)
from app.model.schema.base import (
    EmptyData,
    GenericSuccessResponse,
    ResultSet,
    Success200MetaModel,
    SuccessResponse,
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi_utils import json_response

LOG = log.get_logger()

router = APIRouter(prefix="", tags=["messaging"])


@router.get(
    "/Mail",
    summary="List Emails",
    operation_id="ListEmails",
    responses=get_routers_responses(InvalidParameterError),
)
async def list_mails(
    async_session: DBAsyncSession,
    request_query: Annotated[ListMailsQuery, Query()],
) -> GenericSuccessResponse[ListMailsResponse]:
    """
    Returns email delivery metadata filtered by status.
    """
    stmt = (
        select(Mail.id, Mail.status, Mail.created, Mail.modified)
        .where(Mail.status == request_query.status)
        .order_by(Mail.id)
    )
    total = (
        await async_session.scalar(
            select(func.count())
            .select_from(Mail)
            .where(Mail.status == request_query.status)
        )
        or 0
    )

    if request_query.offset is not None:
        stmt = stmt.offset(request_query.offset)
    if request_query.limit is not None:
        stmt = stmt.limit(request_query.limit)

    mail_list: Sequence[tuple[int, MailStatus, datetime, datetime]] = (
        (await async_session.execute(stmt)).tuples().all()
    )
    mail_data = [
        MailData(
            id=mail_id,
            status=status,
            created=Mail.format_timestamp(created),
            modified=Mail.format_timestamp(modified),
        )
        for mail_id, status, created, modified in mail_list
    ]
    return GenericSuccessResponse[ListMailsResponse](
        meta=Success200MetaModel(code=200, message="OK"),
        data=ListMailsResponse(
            result_set=ResultSet(
                count=total,
                offset=request_query.offset,
                limit=request_query.limit,
                total=total,
            ),
            mails=mail_data,
        ),
    )


@router.post(
    "/Mail",
    summary="Send Email",
    operation_id="SendEmail",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError),
)
async def send_mail(async_session: DBAsyncSession, data: SendMailRequest):
    """
    Sends Email.
    """
    for to_email in data.to_emails:
        mail = Mail()
        mail.to_email = to_email
        mail.subject = data.subject
        mail.text_content = data.text_content or ""
        mail.html_content = data.html_content or ""
        if data.file_content:
            mail.file_content = data.file_content
        if data.file_name:
            mail.file_name = data.file_name
        async_session.add(mail)

    await async_session.commit()

    if TYPE_CHECKING:
        _ = SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK"), data=EmptyData()
        )
    return json_response(SuccessResponse.default())


@router.post(
    "/Mail/Resend",
    summary="Resend failed Emails",
    operation_id="ResendEmails",
    responses=get_routers_responses(DataNotExistsError, InvalidParameterError),
)
async def resend_mails(
    async_session: DBAsyncSession,
    data: ResendMailsRequest,
) -> SuccessResponse:
    """
    Queues selected failed emails for delivery.
    """
    mail_list: Sequence[tuple[int, MailStatus]] = (
        (
            await async_session.execute(
                select(Mail.id, Mail.status).where(Mail.id.in_(data.mail_ids))
            )
        )
        .tuples()
        .all()
    )
    mail_by_id = {mail_id: status for mail_id, status in mail_list}
    missing_mail_ids = [
        mail_id for mail_id in data.mail_ids if mail_id not in mail_by_id
    ]
    if missing_mail_ids:
        raise DataNotExistsError(description=f"id: {missing_mail_ids[0]}")

    non_failed_mail_ids = [
        mail_id for mail_id, status in mail_list if status != MailStatus.FAILED
    ]
    if non_failed_mail_ids:
        raise InvalidParameterError(description="Only failed emails can be resent")

    await async_session.execute(
        update(Mail).where(Mail.id.in_(data.mail_ids)).values(status=MailStatus.PENDING)
    )
    await async_session.commit()

    return SuccessResponse(
        meta=Success200MetaModel(code=200, message="OK"),
        data=EmptyData(),
    )


@router.post(
    "/Chat/Webhook",
    summary="Send chat messages using incoming webhooks",
    operation_id="SendChatWebhook",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError),
)
async def send_chat_webhook(
    async_session: DBAsyncSession, data: SendChatWebhookRequest
):
    """
    Sends Chat Webhook.
    """
    hook = ChatWebhook()
    hook.message = json.dumps(data.message)
    async_session.add(hook)
    await async_session.commit()

    if TYPE_CHECKING:
        _ = SuccessResponse(
            meta=Success200MetaModel(code=200, message="OK"), data=EmptyData()
        )
    return json_response(SuccessResponse.default())
