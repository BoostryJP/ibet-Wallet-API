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
import logging
from smtplib import SMTPException
from unittest.mock import MagicMock

import pytest
from unittest import mock

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.model.db import Mail
from batch.processor_Send_Mail import (
    Processor,
    LOG
)


@pytest.fixture(scope='function')
def processor(session):
    return Processor()


@pytest.fixture(scope="function")
def caplog(caplog: pytest.LogCaptureFixture):
    LOG = logging.getLogger("ibet_wallet_batch")
    default_log_level = LOG.level
    LOG.setLevel(logging.DEBUG)
    LOG.propagate = True
    yield caplog
    LOG.propagate = False
    LOG.setLevel(default_log_level)


class TestProcessorSendMail:

    # Normal_1
    # No unsent email exists
    @mock.patch("app.config.SMTP_SERVER_HOST", "smtp.office365.com")
    @mock.patch("app.config.SMTP_SERVER_PORT", 587)
    @mock.patch("app.config.SMTP_SENDER_EMAIL", "sender@example.com")
    @mock.patch("app.config.SMTP_SENDER_PASSWORD", "password")
    def test_normal_1(self, processor, session, caplog):
        # Run processor
        with mock.patch("app.model.mail.mail.Mail.send_mail", None):
            processor.process()
            session.commit()

        # Assertion
        assert 0 == caplog.record_tuples.count((
            LOG.name,
            logging.INFO,
            "Process end"
        ))

    # Normal_2
    # Unsent email exists
    @mock.patch("app.config.SMTP_SERVER_HOST", "smtp.office365.com")
    @mock.patch("app.config.SMTP_SERVER_PORT", 587)
    @mock.patch("app.config.SMTP_SENDER_EMAIL", "sender@example.com")
    @mock.patch("app.config.SMTP_SENDER_PASSWORD", "password")
    def test_normal_2(self, processor, session, caplog):
        # Prepare data
        mail = Mail()
        mail.to_email = "to@example.com"
        mail.subject = "Test mail"
        mail.text_content = "text content"
        mail.html_content = "<p>html content</p>"
        session.add(mail)
        session.commit()

        # Run processor
        with mock.patch("app.model.mail.mail.Mail.send_mail", return_value = None):
            processor.process()
            session.commit()

        # Assertion
        assert session.query(Mail).all() == []

        assert 1 == caplog.record_tuples.count((
            LOG.name,
            logging.INFO,
            "Process end"
        ))

    # Normal_3
    # SMTPException -> skip
    @mock.patch("app.config.SMTP_SERVER_HOST", "smtp.office365.com")
    @mock.patch("app.config.SMTP_SERVER_PORT", 587)
    @mock.patch("app.config.SMTP_SENDER_EMAIL", "sender@example.com")
    @mock.patch("app.config.SMTP_SENDER_PASSWORD", "password")
    def test_normal_3(self, processor, session, caplog):
        # Prepare data
        mail = Mail()
        mail.to_email = "to@example.com"
        mail.subject = "Test mail"
        mail.text_content = "text content"
        mail.html_content = "<p>html content</p>"
        session.add(mail)
        session.commit()

        # Run processor
        with mock.patch("app.model.mail.mail.Mail.send_mail", MagicMock(side_effect=SMTPException())):
            processor.process()
            session.commit()

        # Assertion
        mail_list = session.query(Mail).all()
        assert len(mail_list) == 1

        assert 1 == caplog.record_tuples.count((
            LOG.name,
            logging.WARNING,
            "Could not send email: "
        ))

        assert 1 == caplog.record_tuples.count((
            LOG.name,
            logging.INFO,
            "Process end"
        ))

    ###########################################################################
    # Error
    ###########################################################################

    # Error_1
    # SQLAlchemyError
    @mock.patch("app.config.SMTP_SERVER_HOST", "smtp.office365.com")
    @mock.patch("app.config.SMTP_SERVER_PORT", 587)
    @mock.patch("app.config.SMTP_SENDER_EMAIL", "sender@example.com")
    @mock.patch("app.config.SMTP_SENDER_PASSWORD", "password")
    def test_error_1(self, processor, session, caplog):
        # Prepare data
        mail = Mail()
        mail.to_email = "to@example.com"
        mail.subject = "Test mail"
        mail.text_content = "text content"
        mail.html_content = "<p>html content</p>"
        session.add(mail)
        session.commit()

        # Run processor
        with mock.patch("app.model.mail.mail.Mail.send_mail", return_value=None),\
                mock.patch.object(Session, "commit", side_effect=SQLAlchemyError()),\
                pytest.raises(SQLAlchemyError):
            processor.process()

        # Assertion
        mail_list = session.query(Mail).all()
        assert len(mail_list) == 1

        assert 0 == caplog.record_tuples.count((
            LOG.name,
            logging.INFO,
            "Process end"
        ))
