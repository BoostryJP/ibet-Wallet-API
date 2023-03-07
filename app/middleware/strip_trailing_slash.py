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
from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

from app import log

from .base import SuppressNoResponseReturnedMiddleware

LOG = log.get_logger()


class StripTrailingSlashMiddleware(SuppressNoResponseReturnedMiddleware):
    """
    Strip Trailing Slash Middleware

    * Used for split trailing slash in URL string.
    *   e.g. If you requests URL like "/Admin/Tokens/",
    *        this middleware replaces it to "/Admin/Tokens" for avoiding redirect(307).
    """

    def __init__(self):
        pass

    async def __call__(
        self, req: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Before process request
        if req.url.path != "/" and req.url.path[-1] == "/":
            replace_path = req.url.path[:-1]
            req._url = req.url.replace(path=replace_path)
            req.scope["path"] = replace_path
            req.scope["raw_path"] = replace_path.encode()

        # Process request
        res: Response = await self.handle(req, call_next)

        # After process request

        return res
