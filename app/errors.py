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


class AppError(Exception):
    status_code = 500
    error_type = "AppError"

    error_code = 0
    message: str = ""
    description: str | dict | None = None

    def __init__(self, description: str | None = None):
        self.description = description


#################################################
# 400 Bad Request
#################################################


class InvalidParameterError(AppError):
    """
    400 ERROR: Invalid Parameter
    """

    status_code = 400
    error_type = "InvalidParameterError"
    error_code = 88
    message = "Invalid Parameter"


class SuspendedTokenError(AppError):
    """
    400 ERROR: Suspended tokens
    """

    status_code = 400
    error_type = "SuspendedTokenError"
    error_code = 20
    message = "Suspended Token"


class ResponseLimitExceededError(AppError):
    """
    400 ERROR: Search results are over the limit
    """

    status_code = 400
    error_type = "ResponseLimitExceededError"
    error_code = 30
    message = "Response Limit Exceeded"


class RequestBlockRangeLimitExceededError(AppError):
    """
    400 ERROR: Search request range is over the limit
    """

    status_code = 400
    error_type = "RequestBlockRangeLimitExceededError"
    error_code = 31
    message = "Request Block Range Limit Exceeded"


#################################################
# 404 Not Found
#################################################


class NotSupportedError(AppError):
    """
    404 ERROR: Unsupported Request
    """

    status_code = 404
    error_type = "NotSupportedError"
    error_code = 10
    message = "Not Supported"

    def __init__(self, method: str | None = None, url: str | None = None):
        description = None
        if method and url:
            description = "method: %s, url: %s" % (method, url)
        super().__init__(description=description)


class DataNotExistsError(AppError):
    """
    404 ERROR: Data not exists
    """

    status_code = 404
    error_type = "DataNotExistsError"
    error_code = 30
    message = "Data Not Exists"


#################################################
# 409 Conflict
#################################################


class DataConflictError(AppError):
    """
    409 ERROR: Data is conflicted
    """

    status_code = 409
    error_type = "DataConflictError"
    error_code = 40
    message = "Data Conflict"


#################################################
# 503 Service Unavailable
#################################################


class ServiceUnavailable(AppError):
    """
    503 ERROR: Service is temporarily unavailable
    """

    status_code = 503
    error_type = "ServiceUnavailable"
    error_code = 503
    message = "Service Unavailable"
