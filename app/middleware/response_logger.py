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

import logging
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import config, log

LOG = log.get_logger()


logging.basicConfig(level=config.LOG_LEVEL)
ACCESS_LOG = logging.getLogger("ibet_wallet_access")
ACCESS_LOG.propagate = False

stream_handler_access = logging.StreamHandler(open(config.ACCESS_LOGFILE, "a"))
formatter_access = logging.Formatter(
    config.INFO_LOG_FORMAT.format("[ACCESS-LOG]"), config.LOG_TIMESTAMP_FORMAT
)
stream_handler_access.setFormatter(formatter_access)
ACCESS_LOG.addHandler(stream_handler_access)


class ResponseLoggerMiddleware:
    """Response Logger Middleware"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Before process request
        request_start_time = time.monotonic()

        method = scope["method"]
        path = scope["path"]
        query_string = scope["query_string"].decode("utf-8")
        status_code = None

        async def send_wrapper(message: Message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        await self.app(scope, receive, send_wrapper)

        # After process request
        response_time = time.monotonic() - request_start_time
        if query_string:
            log_msg = (
                f"{method} {path}?{query_string} {status_code} ({response_time:.6f}sec)"
            )
        else:
            log_msg = f"{method} {path} {status_code} ({response_time:.6f}sec)"
        ACCESS_LOG.info(log_msg)
