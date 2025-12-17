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

import base64
import mimetypes
import smtplib
import ssl
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr

import boto3

from app.config import (
    AWS_SES_REGION_NAME,
    SMTP_AUTH_METHOD,
    SMTP_AUTH_PROVIDER,
    SMTP_METHOD,
    SMTP_POLICY,
    SMTP_SENDER_EMAIL,
    SMTP_SENDER_NAME,
    SMTP_SENDER_PASSWORD,
    SMTP_SERVER_ENCRYPTION_METHOD,
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
)
from app.model.mail.token_provider import MicrosoftTokenProvider


class File:
    name: str
    content: bytes

    def __init__(self, name: str, content: bytes):
        self.name = name
        self.content = content


class Mail:
    def __init__(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: str,
        file: File | None,
    ):
        if SMTP_SENDER_EMAIL is None:
            raise RuntimeError("SMTP sender email is not set.")
        self.sender_email = SMTP_SENDER_EMAIL
        self.to_email = to_email

        if SMTP_METHOD == 0:  # SMTP server
            if SMTP_SERVER_HOST is None or SMTP_SERVER_PORT is None:
                raise RuntimeError("SMTP server host or port is not set.")
            self.server_host = SMTP_SERVER_HOST
            self.server_port = SMTP_SERVER_PORT
            if SMTP_AUTH_METHOD == 0:  # PASSWORD
                self.sender_password = SMTP_SENDER_PASSWORD
            elif SMTP_AUTH_METHOD == 1:  # XOAUTH2
                pass
        elif SMTP_METHOD == 1:  # Amazon SES
            self.aws_region_name = AWS_SES_REGION_NAME
        self.msg = MIMEMultipart("alternative", policy=SMTP_POLICY)
        self.msg.attach(MIMEText(text_content, "plain"))
        self.msg.attach(MIMEText(html_content, "html"))
        self.msg["Subject"] = subject
        self.msg["From"] = formataddr(
            (str(Header(SMTP_SENDER_NAME, "utf-8")), SMTP_SENDER_EMAIL)
        )
        self.msg["To"] = to_email

        if file:
            mimetype, encoding = mimetypes.guess_type(file.name)
            if encoding or mimetype is None:
                mimetype = "application/octet-stream"
            maintype, subtype = mimetype.split("/")
            attach_file = MIMEBase(maintype, subtype)
            attach_file.set_payload(file.content)
            attach_file.add_header("Content-Transfer-Encoding", "base64")
            attach_file.add_header(
                "Content-Disposition", "attachment", filename=file.name
            )
            self.msg.attach(attach_file)

    def send_mail(self):
        if SMTP_METHOD == 0:  # SMTP server
            # Initialize a new smtp client
            if SMTP_SERVER_ENCRYPTION_METHOD == 0:  # STARTTLS
                smtp_client = smtplib.SMTP(
                    host=self.server_host, port=int(self.server_port)
                )
                smtp_client.ehlo()
                smtp_client.starttls()
                smtp_client.ehlo()
            elif SMTP_SERVER_ENCRYPTION_METHOD == 1:  # SSL
                smtp_client = smtplib.SMTP_SSL(
                    host=self.server_host,
                    port=int(self.server_port),
                    context=ssl.create_default_context(),
                )
            else:  # NO-ENCRYPT
                smtp_client = smtplib.SMTP(
                    host=self.server_host, port=int(self.server_port)
                )
            # LOGIN
            if SMTP_AUTH_METHOD == 0:  # PASSWORD
                if self.sender_password is not None:
                    smtp_client.login(self.sender_email, self.sender_password)
            elif SMTP_AUTH_METHOD == 1:  # XOAUTH2
                # Get Access Token
                match SMTP_AUTH_PROVIDER:
                    case "microsoft":
                        token_provider = MicrosoftTokenProvider()
                    case _:
                        raise ValueError(
                            f"Unknown SMTP_AUTH_PROVIDER: {SMTP_AUTH_PROVIDER}"
                        )
                access_token = token_provider.get_access_token()

                # Auth
                auth_str = (
                    f"user={self.sender_email}\x01auth=Bearer {access_token}\x01\x01"
                )
                auth_b64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
                smtp_client.docmd("AUTH", "XOAUTH2 " + auth_b64)

            # Send mail
            try:
                smtp_client.sendmail(
                    self.sender_email, [self.to_email], self.msg.as_bytes()
                )
            finally:
                smtp_client.quit()

        elif SMTP_METHOD == 1:  # Amazon SES
            # Initialize a new smtp client
            smtp_client = boto3.client("ses", region_name=self.aws_region_name)

            # Send mail
            smtp_client.send_raw_email(
                Source=self.sender_email,
                Destinations=[self.to_email],
                RawMessage={
                    "Data": self.msg.as_bytes(),
                },
            )
