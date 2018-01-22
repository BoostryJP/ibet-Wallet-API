# -*- coding: utf-8 -*-
import os

import falcon

from app import log
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session

from app.api.common import base
from app.api.v1 import issuers

from app.errors import AppError

LOG = log.get_logger()

class App(falcon.API):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())
        self.add_route('/v1/users', issuers.Collection())
        self.add_route('/v1/users/{user_id}', issuers.Item())

        self.add_error_handler(AppError, AppError.handle)

init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
