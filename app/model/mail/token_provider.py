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
import os
import time
import uuid

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from pydantic import BaseModel, ValidationError
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from app.config import (
    SMTP_MS_CLIENT_CERT_PATH,
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

    @staticmethod
    def _generate_client_assertion(
        client_id: str, tenant_id: str, private_key_path: str
    ) -> str:
        """
        Generate JWT Client Assertion signed with the certificate's private key.
        """
        try:
            with open(private_key_path, "rb") as key_file:
                private_key = serialization.load_pem_private_key(
                    key_file.read(), password=None
                )
        except Exception as e:
            raise ValueError(f"Failed to load private key from {private_key_path}: {e}")

        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise ValueError("Private key must be an RSA key")

        # JWT Claims
        now = time.time()
        # Header
        header = {
            "alg": "RS256",
            "typ": "JWT",
            "x5t": None,  # x5t (Thumbprint) is optional but recommended if available.
        }
        # Payload
        payload = {
            "iss": client_id,
            "sub": client_id,
            "aud": f"https://login.microsoftonline.com/{tenant_id}/v2.0/token",
            "jti": str(uuid.uuid4()),
            "nbf": int(now),
            "exp": int(now) + 300,  # 5 minutes expiration
        }

        # NOTE: Since pyjwt is not guaranteed to be in the environment,
        # and installing new dependencies might not be desired,
        # we construct the JWT manually using cryptography for signing.
        # This is compliant with RFC 7515.

        def b64url_encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

        # 1. Create Signing Input
        encoded_header = b64url_encode(json.dumps(header).encode("utf-8"))
        encoded_payload = b64url_encode(json.dumps(payload).encode("utf-8"))
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")

        # 2. Sign
        signature = private_key.sign(
            signing_input,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        # 3. Concatenate
        encoded_signature = b64url_encode(signature)
        return f"{encoded_header}.{encoded_payload}.{encoded_signature}"

    def get_access_token(self) -> str:
        # Return cached token if valid (with 60 seconds safety buffer)
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        tenant_id = SMTP_MS_TENANT_ID
        client_id = SMTP_MS_CLIENT_ID
        client_secret = SMTP_MS_CLIENT_SECRET
        cert_path = SMTP_MS_CLIENT_CERT_PATH

        if tenant_id is None or client_id is None:
            raise ValueError("Missing Microsoft OAuth configuration")

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "scope": "https://outlook.office365.com/.default",
        }

        # Determine authentication method: Certificate (Client Assertion) or Secret
        use_cert_auth = False
        if cert_path and os.path.exists(cert_path):
            use_cert_auth = True
        elif not client_secret:
            raise ValueError(
                "Missing Microsoft OAuth configuration: Neither Client Secret nor Certificate is available."
            )

        if use_cert_auth:
            try:
                client_assertion = self._generate_client_assertion(
                    client_id, tenant_id, cert_path
                )
                data["client_assertion_type"] = (
                    "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
                )
                data["client_assertion"] = client_assertion
            except Exception as e:
                raise RuntimeError(
                    f"Failed to generate client assertion from certificate: {e}"
                ) from e
        else:
            data["client_secret"] = client_secret

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
