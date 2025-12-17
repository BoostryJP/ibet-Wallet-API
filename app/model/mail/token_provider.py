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

import abc
import base64
import json
import time
import uuid

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ValidationError
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from app.config import (
    SMTP_MS_CLIENT_ID,
    SMTP_MS_CLIENT_SECRET,
    SMTP_MS_TENANT_ID,
)


class TokenProvider(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_access_token(self) -> str:
        """
        Get access token for authentication
        """
        pass


class MicrosoftTokenResponse(BaseModel):
    """
    Schema for Microsoft Identity Platform token response
    """

    access_token: str
    expires_in: int
    token_type: str


class MicrosoftTokenProvider(TokenProvider):
    """
    Provider that fetches access token from Microsoft Identity Platform
    using a Refresh Token.
    """

    _access_token: str | None = None
    _token_expiry: float = 0.0

    def get_access_token(self) -> str:
        # Return cached token if valid (with 60 seconds safety buffer)
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        tenant_id = SMTP_MS_TENANT_ID
        client_id = SMTP_MS_CLIENT_ID
        client_secret = SMTP_MS_CLIENT_SECRET

        if tenant_id is None or client_id is None or (client_secret is None):
            raise ValueError("Missing Microsoft OAuth configuration")

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "https://outlook.office365.com/.default",
        }

        try:
            with requests.Session() as session:
                retries = Retry(
                    total=3,
                    backoff_factor=1,
                    status_forcelist=[500, 502, 503, 504],
                    allowed_methods=["POST"],
                )
                adapter = HTTPAdapter(max_retries=retries)
                session.mount("https://", adapter)

                response = session.post(token_url, data=data, timeout=10)
                response.raise_for_status()

                # Validate response schema
                token_data = MicrosoftTokenResponse.model_validate(response.json())

                # Update cache
                self.__class__._access_token = token_data.access_token
                # Set expiry time relative to now
                self.__class__._token_expiry = time.time() + token_data.expires_in

                return token_data.access_token

        except (requests.exceptions.RequestException, ValidationError) as e:
            # You might want to log this error in a real app
            raise RuntimeError(f"Failed to refresh access token: {str(e)}") from e
