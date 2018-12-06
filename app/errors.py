# -*- coding: utf-8 -*-

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


ERR_USER_NOT_EXISTS = {
    'status': falcon.HTTP_404,
    'code': 21,
    'title': 'User Not Exists'
}

ERR_PASSWORD_NOT_MATCH = {
    'status': falcon.HTTP_400,
    'code': 22,
    'title': 'Password Not Match'
}

ERR_DATA_NOT_EXISTS = {
    'status': falcon.HTTP_404,
    'code': 30,
    'title': 'Data Not Exists'
}

ERR_ETH_VALUE_ERROR = {
    'status': falcon.HTTP_400,
    'code': 40,
    'title': 'Eth ValueError'
}

ERR_SNS_NOTFOUND_ERROR = {
    'status': falcon.HTTP_404,
    'code': 50,
    'title': 'SNS NotFoundError'
}

ERR_INVALID_CARD_ERROR = {
    'status': falcon.HTTP_400,
    'code': 60,
    'title': 'Invalid Credit Card'
}


class AppError(Exception):
    def __init__(self, error=ERR_UNKNOWN, description=None):
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
    def __init__(self, description=None):
        super().__init__(ERR_INVALID_PARAMETER)
        self.error['description'] = description


class DatabaseError(AppError):
    def __init__(self, error, args=None, params=None):
        super().__init__(error)
        obj = OrderedDict()
        obj['details'] = ', '.join(args)
        obj['params'] = str(params)
        self.error['description'] = obj


class NotSupportedError(AppError):
    def __init__(self, method=None, url=None):
        super().__init__(ERR_NOT_SUPPORTED)
        if method and url:
            self.error['description'] = 'method: %s, url: %s' % (method, url)


class UserNotExistsError(AppError):
    def __init__(self, description=None):
        super().__init__(ERR_USER_NOT_EXISTS)
        self.error['description'] = description


class PasswordNotMatch(AppError):
    def __init__(self, description=None):
        super().__init__(ERR_PASSWORD_NOT_MATCH)
        self.error['description'] = description


class DataNotExistsError(AppError):
    def __init__(self, description=None):
        super().__init__(ERR_DATA_NOT_EXISTS)
        self.error['description'] = description

class EthValueError(AppError):
    def __init__(self, code=None, message=None):
        super().__init__(ERR_ETH_VALUE_ERROR)
        self.error['description'] = 'code: %i, message: %s' % (code, message)

class SNSNotFoundError(AppError):
    def __init__(self, description=None):
        super().__init__(ERR_SNS_NOTFOUND_ERROR)
        self.error['description'] = description

class InvalidCardError(AppError):
    def __init__(self, description=None):
        super().__init__(ERR_INVALID_CARD_ERROR)
        self.error['description'] = description
