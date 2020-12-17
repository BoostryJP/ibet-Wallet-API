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

import json
import falcon

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict

OK = {
    'status': falcon.HTTP_200,
    'code': 200,
}

ERR_UNKNOWN = {
    'status': falcon.HTTP_500,
    'code': 500,
    'title': 'Unknown Error'
}

ERR_INVALID_PARAMETER = {
    'status': falcon.HTTP_400,
    'code': 88,
    'title': 'Invalid Parameter'
}

ERR_DATABASE_ROLLBACK = {
    'status': falcon.HTTP_500,
    'code': 77,
    'title': 'Database Rollback Error'
}

ERR_NOT_SUPPORTED = {
    'status': falcon.HTTP_404,
    'code': 10,
    'title': 'Not Supported'
}

ERR_SUSPENDED_TOKEN = {
    'status': falcon.HTTP_400,
    'code': 20,
    'title': 'Suspended Token'
}

ERR_DATA_NOT_EXISTS = {
    'status': falcon.HTTP_404,
    'code': 30,
    'title': 'Data Not Exists'
}


class AppError(Exception):
    def __init__(self, error=None, description=None):
        if error is None:
            error = ERR_UNKNOWN
        self.error = error
        self.error['description'] = description

    @property
    def code(self):
        return self.error['code']

    @property
    def title(self):
        return self.error['title']

    @property
    def status(self):
        return self.error['status']

    @property
    def description(self):
        return self.error['description']

    @staticmethod
    def handle(exception, req, res, error=None):
        res.status = exception.status
        meta = OrderedDict()
        meta['code'] = exception.code
        meta['message'] = exception.title
        if exception.description:
            meta['description'] = exception.description
        res.body = json.dumps({'meta': meta})


class InvalidParameterError(AppError):
    """
    400 ERROR: 無効なパラメータ
    """
    def __init__(self, description=None):
        super().__init__(ERR_INVALID_PARAMETER)
        self.error['description'] = description


class DatabaseError(AppError):
    """
    500 ERROR: データベースエラー
    """
    def __init__(self, error, args=None, params=None):
        super().__init__(error)
        obj = OrderedDict()
        obj['details'] = ', '.join(args)
        obj['params'] = str(params)
        self.error['description'] = obj


class NotSupportedError(AppError):
    """
    404 ERROR: サポートしていないHTTPメソッド
    """
    def __init__(self, method=None, url=None):
        super().__init__(ERR_NOT_SUPPORTED)
        if method and url:
            self.error['description'] = 'method: %s, url: %s' % (method, url)


class DataNotExistsError(AppError):
    """
    404 ERROR: データが存在しない
    """
    def __init__(self, description=None):
        super().__init__(ERR_DATA_NOT_EXISTS)
        self.error['description'] = description


class SuspendedTokenError(AppError):
    """
    400 ERROR: 取扱停止中のトークン
    """
    def __init__(self, description=None):
        super().__init__(ERR_SUSPENDED_TOKEN)
        self.error['description'] = description
