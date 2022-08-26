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

from collections import OrderedDict
from pydantic import (
    BaseModel,
    Field
)


class ErrorInfo(BaseModel):
    status_code: int
    error_code: int
    message: str | None = Field(default=None)
    description: str | dict| None = Field(default=None)


ERR_UNKNOWN = ErrorInfo(status_code=500, error_code=500, message="Unknown Error")

ERR_INVALID_PARAMETER = ErrorInfo(status_code=400, error_code=88, message="Invalid Parameter")

ERR_DATABASE_ROLLBACK = ErrorInfo(status_code=500, error_code=77, message="Database Rollback Error")

ERR_NOT_SUPPORTED = ErrorInfo(status_code=404, error_code=10, message="Not Supported")

ERR_SUSPENDED_TOKEN = ErrorInfo(status_code=400, error_code=20, message="Suspended Token")

ERR_DATA_NOT_EXISTS = ErrorInfo(status_code=404, error_code=30, message="Data Not Exists")

ERR_DATA_CONFLICT = ErrorInfo(status_code=409, error_code=40, message="Data Conflict")

ERR_SERVICE_UNAVAILABLE = ErrorInfo(status_code=503, error_code=503, message="Service Unavailable")


class AppError(Exception):
    error: ErrorInfo

    def __init__(self, error: ErrorInfo | None = None, message: str | None = None):
        if error is None:
            error = ErrorInfo(status_code=500, error_code=500, message="Unknown Error")
        self.error = error
        if message is not None:
            self.error.message = message

    @property
    def code(self):
        return self.error.error_code

    @property
    def message(self):
        return self.error.message

    @property
    def status(self):
        return self.error.status_code

    @property
    def description(self):
        return self.error.description


class InvalidParameterError(AppError):
    """
    400 ERROR: 無効なパラメータ
    """
    def __init__(self, description=None):
        super().__init__(ERR_INVALID_PARAMETER)
        self.error.description = description


class DatabaseError(AppError):
    """
    500 ERROR: データベースエラー
    """
    def __init__(self, error, args=None):
        super().__init__(error)
        obj = OrderedDict()
        obj['details'] = ', '.join(args)
        self.error.message = obj


class NotSupportedError(AppError):
    """
    404 ERROR: サポートしていないHTTPメソッド
    """
    def __init__(self, method: str | None = None, url: str | None = None):
        super().__init__(ERR_NOT_SUPPORTED)
        if method and url:
            self.error.description = 'method: %s, url: %s' % (method, url)


class DataNotExistsError(AppError):
    """
    404 ERROR: データが存在しない
    """
    def __init__(self, description: str | None = None):
        super().__init__(ERR_DATA_NOT_EXISTS)
        self.error.description = description


class SuspendedTokenError(AppError):
    """
    400 ERROR: 取扱停止中のトークン
    """
    def __init__(self, description: str | None = None):
        super().__init__(ERR_SUSPENDED_TOKEN)
        self.error.description = description


class DataConflictError(AppError):
    """
    409 ERROR: データが重複
    """
    def __init__(self, description=None):
        super().__init__(ERR_DATA_CONFLICT)
        self.error.description = description


class ServiceUnavailable(AppError):
    """
    503 ERROR: サービス利用不可
    """
    def __init__(self, description=None):
        super().__init__(ERR_SERVICE_UNAVAILABLE)
        self.error.description = description
