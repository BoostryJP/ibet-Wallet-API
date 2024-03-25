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
from datetime import datetime

from fastapi import Request, Response
from starlette.middleware.base import RequestResponseEndpoint

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

    def __init__(self):
        pass

    async def __call__(
        self, req: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Before process request
        request_start_time = datetime.utcnow()

        # Process request
        res: Response = await call_next(req)

        # After process request
        if req.url.path != "/":
            response_time = (datetime.utcnow() - request_start_time).total_seconds()
            if req.url.query:
                log_msg = f"{req.method} {req.url.path}?{req.url.query} {res.status_code} ({response_time}sec)"
            else:
                log_msg = f"{req.method} {req.url.path} {res.status_code} ({response_time}sec)"
            ACCESS_LOG.info(log_msg)

        return res
