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
import json
from unittest.mock import MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.model.mail.token_provider import MicrosoftTokenProvider


class TestMicrosoftTokenProviderCert:
    """
    Unit tests for app.model.mail.token_provider.MicrosoftTokenProvider
    Focusing on Certificate Authentication (Client Assertion)
    """

    @pytest.fixture
    def mock_private_key(self):
        # Generate a temporary RSA private key for testing
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        return pem

    def test_get_access_token_with_certificate(self, mock_private_key, tmp_path):
        """
        Verify that get_access_token uses Client Assertion when certificate is available
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        # Create dummy certificate file
        cert_file = tmp_path / "test_cert.pem"
        cert_file.write_bytes(mock_private_key)
        cert_path_str = str(cert_file)

        # Arrange
        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            # Client Secret is mocked to None to ensure fallback logic passes if using cert
            # But the code shouldn't use it anyway if cert is present.
            # Let's provide a dummy secret to ensure it's NOT used.
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch(
                "app.model.mail.token_provider.SMTP_MS_CLIENT_CERT_PATH", cert_path_str
            ),
            patch("requests.Session.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "valid_access_token_via_cert",
                "expires_in": 3599,
                "token_type": "Bearer",
            }
            mock_post.return_value = mock_response

            provider = MicrosoftTokenProvider()

            # Act
            token = provider.get_access_token()

            # Assert
            assert token == "valid_access_token_via_cert"

            # Verify request data
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            data = kwargs["data"]

            # Key checks
            assert (
                data["client_assertion_type"]
                == "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
            )
            assert "client_assertion" in data
            assert "client_secret" not in data  # MUST NOT send secret if using cert
            assert data["grant_type"] == "client_credentials"  # Updated check

            # Verify JWT structure
            client_assertion = data["client_assertion"]
            parts = client_assertion.split(".")
            assert len(parts) == 3

            # Verify Header
            header = json.loads(
                base64.urlsafe_b64decode(parts[0] + "==").decode("utf-8")
            )
            assert header["alg"] == "RS256"
            assert header["typ"] == "JWT"

            # Verify Payload
            payload = json.loads(
                base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8")
            )
            assert payload["iss"] == "client-1"
            assert payload["sub"] == "client-1"
            assert (
                payload["aud"]
                == "https://login.microsoftonline.com/tenant-1/v2.0/token"
            )
            assert "jti" in payload
            assert "exp" in payload

    def test_get_access_token_fallback_to_secret(self):
        """
        Verify that get_access_token falls back to Client Secret if certificate file does not exist
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        # Arrange
        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch(
                "app.model.mail.token_provider.SMTP_MS_CLIENT_CERT_PATH",
                "/non/existent/path.pem",
            ),
            patch("requests.Session.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "valid_access_token_via_secret",
                "expires_in": 3599,
                "token_type": "Bearer",
            }
            mock_post.return_value = mock_response

            provider = MicrosoftTokenProvider()

            # Act
            token = provider.get_access_token()

            # Assert
            assert token == "valid_access_token_via_secret"

            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            data = kwargs["data"]

            assert "client_secret" in data
            assert data["client_secret"] == "secret-1"
            assert "client_assertion" not in data
            assert data["grant_type"] == "client_credentials"

    def test_get_access_token_no_auth_available(self):
        """
        Verify that ValueError is raised if neither secret nor certificate is available
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", None),
            patch(
                "app.model.mail.token_provider.SMTP_MS_CLIENT_CERT_PATH",
                "/non/existent/path.pem",
            ),
        ):
            provider = MicrosoftTokenProvider()

            with pytest.raises(
                ValueError, match="Neither Client Secret nor Certificate is available"
            ):
                provider.get_access_token()
