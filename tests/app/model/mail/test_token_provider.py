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

import pytest
import requests
from requests.adapters import HTTPAdapter

from app.model.mail.token_provider import MicrosoftTokenProvider


class TestMicrosoftTokenProvider:
    """
    Unit tests for app.model.mail.token_provider.MicrosoftTokenProvider
    """

    def test_get_access_token_success(self):
        """
        Verify that get_access_token correctly parses successful response
        """
        # Arrange
        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch("app.model.mail.token_provider.SMTP_MS_REFRESH_TOKEN", "refresh-1"),
            patch("requests.Session.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "token_type": "Bearer",
                "scope": "https://outlook.office365.com/.default",
                "expires_in": 3599,
                "ext_expires_in": 3599,
                "access_token": "valid_access_token",
                "refresh_token": "new_refresh_token",
            }
            mock_post.return_value = mock_response

            provider = MicrosoftTokenProvider()

            # Act
            token = provider.get_access_token()

            # Assert
            assert token == "valid_access_token"

    def test_get_access_token_missing_config(self):
        """
        Verify that missing config raises ValueError
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        with patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", None):
            provider = MicrosoftTokenProvider()
            with pytest.raises(
                ValueError, match="Missing Microsoft OAuth configuration"
            ):
                provider.get_access_token()

    def test_get_access_token_api_error(self):
        """
        Verify that API error raises RuntimeError
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        # Arrange
        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch("app.model.mail.token_provider.SMTP_MS_REFRESH_TOKEN", "refresh-1"),
            patch("requests.Session.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "400 Bad Request"
            )
            mock_post.return_value = mock_response

            provider = MicrosoftTokenProvider()

            # Act & Assert
            with pytest.raises(RuntimeError, match="Failed to refresh access token"):
                provider.get_access_token()

    def test_get_access_token_validation_error(self):
        """
        Verify that invalid response schema raises RuntimeError (wrapping ValidationError)
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        # Arrange
        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch("app.model.mail.token_provider.SMTP_MS_REFRESH_TOKEN", "refresh-1"),
            patch("requests.Session.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            # Missing expires_in (and token_type) will cause validation error
            mock_response.json.return_value = {"access_token": "valid_access_token"}
            mock_post.return_value = mock_response

            provider = MicrosoftTokenProvider()

            # Act & Assert
            with pytest.raises(RuntimeError, match="Failed to refresh access token"):
                provider.get_access_token()

    def test_get_access_token_retry_logic(self):
        """
        Verify that retries are configured
        """
        # Ensure cache is empty
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

        # Arrange
        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch("app.model.mail.token_provider.SMTP_MS_REFRESH_TOKEN", "refresh-1"),
            patch("requests.Session.post") as mock_post,
            patch("requests.Session.mount") as mock_mount,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "retry_token",
                "expires_in": 3599,
                "token_type": "Bearer",
            }
            mock_post.return_value = mock_response

            provider = MicrosoftTokenProvider()
            provider.get_access_token()

            # Verify adapter mount
            mock_mount.assert_called()
            args, _ = mock_mount.call_args
            adapter = args[1]
            assert isinstance(adapter, HTTPAdapter)
            assert adapter.max_retries.total == 3
            assert adapter.max_retries.status_forcelist == [500, 502, 503, 504]

    def test_get_access_token_cache_hit(self):
        """
        Verify that cached token is returned if valid
        """
        import time

        # Manually set cache
        future_time = time.time() + 3600
        MicrosoftTokenProvider._access_token = "cached_token"
        MicrosoftTokenProvider._token_expiry = future_time

        provider = MicrosoftTokenProvider()

        with patch("requests.Session.post") as mock_post:
            token = provider.get_access_token()

            assert token == "cached_token"
            mock_post.assert_not_called()

        # Cleanup
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0

    def test_get_access_token_cache_renew(self):
        """
        Verify that token is renewed if cache is expired
        """
        import time
        from unittest.mock import MagicMock

        # Manually set expired cache
        past_time = time.time() - 3600
        MicrosoftTokenProvider._access_token = "old_token"
        MicrosoftTokenProvider._token_expiry = past_time

        provider = MicrosoftTokenProvider()

        with (
            patch("app.model.mail.token_provider.SMTP_MS_TENANT_ID", "tenant-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_ID", "client-1"),
            patch("app.model.mail.token_provider.SMTP_MS_CLIENT_SECRET", "secret-1"),
            patch("app.model.mail.token_provider.SMTP_MS_REFRESH_TOKEN", "refresh-1"),
            patch("requests.Session.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_token",
                "expires_in": 3599,
                "token_type": "Bearer",
            }
            mock_post.return_value = mock_response

            token = provider.get_access_token()

            assert token == "new_token"
            mock_post.assert_called_once()

            # Verify cache updated
            assert MicrosoftTokenProvider._access_token == "new_token"
            assert MicrosoftTokenProvider._token_expiry > time.time() + 3500

        # Cleanup
        MicrosoftTokenProvider._access_token = None
        MicrosoftTokenProvider._token_expiry = 0.0
