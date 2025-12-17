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

from unittest.mock import MagicMock, patch

from app.model.mail import Mail


@patch(
    "app.model.mail.mail.SMTP_SENDER_EMAIL",
    "test@example.com",
)
@patch(
    "app.model.mail.mail.SMTP_SERVER_HOST",
    "example.com",
)
@patch(
    "app.model.mail.mail.SMTP_SERVER_PORT",
    587,
)
class TestMailUnit:
    """
    Unit tests for app.model.mail.Mail
    Mocks smtplib to verify command interactions
    """

    def test_send_mail_password_auth(self):
        """
        Verify that PASSWORD auth (default) calls login()
        """
        # Arrange
        with (
            patch("app.model.mail.mail.SMTP_METHOD", 0),
            patch("app.model.mail.mail.SMTP_AUTH_METHOD", 0),
            patch("app.model.mail.mail.SMTP_SENDER_NAME", "Sender Name"),
            patch("app.model.mail.mail.SMTP_SENDER_EMAIL", "sender@example.com"),
            patch("smtplib.SMTP") as mock_smtp_cls,
        ):
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value = mock_smtp

            mail = Mail(
                to_email="test@example.com",
                subject="Test Subject",
                text_content="Body",
                html_content="<p>Body</p>",
                file=None,
            )
            mail.sender_password = "password"

            # Act
            mail.send_mail()

            # Assert
            mock_smtp.login.assert_called_once()
            mock_smtp.docmd.assert_not_called()
            mock_smtp.sendmail.assert_called_once()
            mock_smtp.quit.assert_called_once()

    def test_send_mail_xoauth2_auth(self):
        """
        Verify that XOAUTH2 auth calls docmd("AUTH", ...)
        """
        # Arrange
        with (
            patch("app.model.mail.mail.SMTP_METHOD", 0),
            patch("app.model.mail.mail.SMTP_AUTH_METHOD", 1),
            patch("app.model.mail.mail.SMTP_SENDER_NAME", "Sender Name"),
            patch("app.model.mail.mail.SMTP_SENDER_EMAIL", "sender@example.com"),
            patch("app.config.SMTP_AUTH_PROVIDER", "microsoft"),
            patch("app.model.mail.mail.MicrosoftTokenProvider") as MockTokenProvider,
            patch("smtplib.SMTP") as mock_smtp_cls,
        ):
            mock_smtp = MagicMock()
            mock_smtp_cls.return_value = mock_smtp

            mock_token_provider = MagicMock()
            MockTokenProvider.return_value = mock_token_provider
            mock_token_provider.get_access_token.return_value = "test_token"

            mail = Mail(
                to_email="test@example.com",
                subject="Test Subject",
                text_content="Body",
                html_content="<p>Body</p>",
                file=None,
            )

            # Act
            mail.send_mail()

            # Assert
            mock_smtp.login.assert_not_called()

            # Verify AUTH XOAUTH2 command
            # Expected auth string: user=<sender>\x01auth=Bearer <token>\x01\x01
            # Note: config.SMTP_SENDER_EMAIL is mocked/defaulted during imports,
            # ideally we should patch it if we want to be strict about the content.
            # Here we just check if docmd was called with AUTH
            mock_smtp.docmd.assert_called_once()
            args, _ = mock_smtp.docmd.call_args
            assert args[0] == "AUTH"
            assert args[1].startswith("XOAUTH2 ")

            # Verify basic structure of the base64 encoded part
            import base64

            sent_b64 = args[1].split(" ")[1]
            decoded_auth = base64.b64decode(sent_b64).decode("utf-8")
            assert "user=sender@example.com" in decoded_auth
            assert "auth=Bearer test_token" in decoded_auth
            assert decoded_auth.endswith("\x01\x01")

            mock_smtp.sendmail.assert_called_once()
            mock_smtp.quit.assert_called_once()
