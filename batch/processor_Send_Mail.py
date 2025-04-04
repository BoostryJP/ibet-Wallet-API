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
import time
from smtplib import SMTPException
from typing import Sequence

from botocore.exceptions import ClientError as SESException
from sqlalchemy import create_engine, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app import config
from app.model.db import Mail
from app.model.mail import File, Mail as SMTPMail
from batch import free_malloc, log

LOG = log.get_logger(process_name="PROCESSOR-SEND-MAIL")

db_engine = create_engine(config.DATABASE_URL, echo=False, pool_pre_ping=True)


class Processor:
    def process(self):
        db_session = Session(autocommit=False, autoflush=True, bind=db_engine)
        try:
            mail_list: Sequence[Mail] = db_session.scalars(select(Mail)).all()
            if len(mail_list) > 0:
                LOG.info("Process start")
                for mail in mail_list:
                    try:
                        # Not send emails if the domain is not allowed
                        if (
                            config.ALLOWED_EMAIL_DESTINATION_DOMAIN_LIST is not None
                            and mail.to_email.split("@")[1]
                            not in config.ALLOWED_EMAIL_DESTINATION_DOMAIN_LIST
                        ):
                            LOG.notice(
                                f"Destination address is not allowed to send: id={mail.id}"
                            )
                            continue

                        # Not send emails if the destination address is not allowed
                        if (
                            config.DISALLOWED_DESTINATION_EMAIL_ADDRESS_REGEX
                            is not None
                            and bool(
                                re.fullmatch(
                                    config.DISALLOWED_DESTINATION_EMAIL_ADDRESS_REGEX,
                                    mail.to_email,
                                )
                            )
                        ):
                            LOG.notice(
                                f"Destination address is not allowed to send: id={mail.id}"
                            )
                            continue

                        file = None
                        if mail.file_name and mail.file_content:
                            file = File(name=mail.file_name, content=mail.file_content)
                        smtp_mail = SMTPMail(
                            to_email=mail.to_email,
                            subject=mail.subject,
                            text_content=mail.text_content,
                            html_content=mail.html_content,
                            file=file,
                        )
                        smtp_mail.send_mail()
                    except (SMTPException, SESException, IndexError):
                        LOG.warning(f"Could not send email: id={mail.id}")
                        continue
                    finally:
                        db_session.delete(mail)
                        db_session.commit()
                LOG.info("Process end")
        finally:
            db_session.close()


def main():
    LOG.info("Service started successfully")
    processor = Processor()
    while True:
        start_time = time.time()
        try:
            processor.process()
        except SQLAlchemyError as sa_err:
            LOG.error(f"A database error has occurred: code={sa_err.code}\n{sa_err}")
        except Exception as ex:
            LOG.exception(ex)

        elapsed_time = time.time() - start_time
        time.sleep(max(30 - elapsed_time, 0))
        free_malloc()


if __name__ == "__main__":
    main()
