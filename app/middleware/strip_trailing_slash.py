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

from urllib.parse import urlparse, urlunparse

from starlette.types import ASGIApp, Receive, Scope, Send

from app import log

LOG = log.get_logger()


class StripTrailingSlashMiddleware:
    """
    Strip Trailing Slash Middleware

    * Used for split trailing slash in URL string.
    *   e.g. If you requests URL like "/Admin/Tokens/",
    *        this middleware replaces it to "/Admin/Tokens" for avoiding redirect(307).
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Before process request
        path = scope["path"]
        if path != "/" and path.endswith("/"):
            # Remove trailing slash
            new_path = path.rstrip("/")

            # Update scope
            scope["path"] = new_path
            scope["raw_path"] = new_path.encode()

            # Update url in scope
            if "url" in scope:
                url_parts = list(urlparse(str(scope["url"])))
                url_parts[2] = new_path  # Update path
                scope["url"] = urlunparse(url_parts)

        # Process request
        await self.app(scope, receive, send)
