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
from fastapi import (
    APIRouter,
    Depends
)
from sqlalchemy.orm import Session

from app import log
from app.database import db_session
from app.errors import InvalidParameterError
from app.model.db import Mail
from app.model.schema import (
    SuccessResponse,
    SendMailRequest
)
from app.utils.docs_utils import get_routers_responses
from app.utils.fastapi import json_response

LOG = log.get_logger()

router = APIRouter(
    prefix="/Mail",
    tags=["messaging"]
)


@router.post(
    "",
    summary="Send Email",
    operation_id="SendEmail",
    response_model=SuccessResponse,
    responses=get_routers_responses(InvalidParameterError),
)
def send_mail(
    data: SendMailRequest,
    session: Session = Depends(db_session)
):
    """Send Email"""
    for to_email in data.to_emails:
        mail = Mail()
        mail.to_email = to_email
        mail.subject = data.subject
        mail.text_content = data.text_content
        mail.html_content = data.html_content
        session.add(mail)

    session.commit()

    return json_response(SuccessResponse.default())
