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


class Mail:

    def __init__(self,
                 server_host: str, server_port: int,
                 sender_email: str, to_email: str,
                 subject: str, text_content: str, html_content: str):
        self.server_host = server_host
        self.server_port = server_port
        self.sender_email = sender_email
        self.to_email = to_email

        self.msg = MIMEMultipart("alternative")
        self.msg.attach(MIMEText(text_content, "plain"))
        self.msg.attach(MIMEText(html_content, "html"))
        self.msg["Subject"] = subject
        self.msg["From"] = sender_email
        self.msg["To"] = to_email

    def send_mail(self, password: str):
        # Initialize a new smtp client
        smtp_client = smtplib.SMTP(self.server_host, self.server_port)
        smtp_client.ehlo()

        # STARTTLS
        smtp_client.starttls()
        smtp_client.ehlo()

        # LOGIN
        smtp_client.login(self.sender_email, password)

        # Send mail
        try:
            smtp_client.sendmail(
                self.sender_email,
                [self.to_email],
                self.msg.as_bytes()
            )
        finally:
            smtp_client.quit()
