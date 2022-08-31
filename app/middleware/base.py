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
from fastapi import (
    Request,
    Response,
    status
)

from starlette.middleware.base import RequestResponseEndpoint
from app import log

LOG = log.get_logger()


class SuppressNoResponseReturnedMiddleware:
    """
    Supress "No Response Returned" Middleware Base Class

    * This is supposed to be inherited from other middleware class
    * for handling exception thrown when clients disconnect while server process requests.
    *
    * Based on: https://github.com/encode/starlette/discussions/1527#discussioncomment-2234702
    """
    @staticmethod
    async def handle(request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except RuntimeError as e:
            if await request.is_disconnected() and str(e) == "No response returned.":
                LOG.warning(
                    "Error `No response returned` detected. "
                    "At the same time we know that the client is disconnected "
                    "and not waiting for a response."
                )

                return Response(status_code=status.HTTP_204_NO_CONTENT)
            else:
                raise
        return response
