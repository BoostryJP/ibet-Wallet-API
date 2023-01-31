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
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import boto3

from app.config import (
    SMTP_METHOD,
    SMTP_SENDER_NAME,
    SMTP_SENDER_EMAIL,
    SMTP_SERVER_HOST,
    SMTP_SERVER_PORT,
    SMTP_SENDER_PASSWORD,
    AWS_SES_REGION_NAME
)


class Mail:

    def __init__(self, to_email: str, subject: str, text_content: str, html_content: str):
        self.sender_email = SMTP_SENDER_EMAIL
        self.to_email = to_email

        if SMTP_METHOD == 0:  # SMTP server
            self.server_host = SMTP_SERVER_HOST
            self.server_port = SMTP_SERVER_PORT
            self.sender_password = SMTP_SENDER_PASSWORD
        elif SMTP_METHOD == 1:  # Amazon SES
            self.aws_region_name = AWS_SES_REGION_NAME

        self.msg = MIMEMultipart("alternative")
        self.msg.attach(MIMEText(text_content, "plain"))
        self.msg.attach(MIMEText(html_content, "html"))
        self.msg["Subject"] = subject
        self.msg["From"] = f"{SMTP_SENDER_NAME} <{SMTP_SENDER_EMAIL}>"
        self.msg["To"] = to_email

    def send_mail(self):
        if SMTP_METHOD == 0:  # SMTP server
            # Initialize a new smtp client
            smtp_client = smtplib.SMTP(self.server_host, self.server_port)
            smtp_client.ehlo()

            # STARTTLS
            smtp_client.starttls()
            smtp_client.ehlo()

            # LOGIN
            smtp_client.login(self.sender_email, self.sender_password)

            # Send mail
            try:
                smtp_client.sendmail(
                    self.sender_email,
                    [self.to_email],
                    self.msg.as_bytes()
                )
            finally:
                smtp_client.quit()

        elif SMTP_METHOD == 1:  # Amazon SES
            # Initialize a new smtp client
            smtp_client = boto3.client("ses", region_name=self.aws_region_name)

            # Send mail
            smtp_client.send_raw_email(
                Source=self.sender_email,
                Destinations=[
                    self.to_email
                ],
                RawMessage={
                    "Data": self.msg.as_bytes(),
                }
            )
