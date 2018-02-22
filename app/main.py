# -*- coding: utf-8 -*-
import os

import falcon

from app import log
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session

from app.api.common import base
from app.api.v1 import eth
from app.api.v1 import issuers
from app.api.v1 import tokenTemplates
from app.api.v1 import contracts
from app.api.v1 import position

from app.errors import AppError

LOG = log.get_logger()

class App(falcon.API):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())

        # Ethereum
        self.add_route('/v1/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())

        # 発行体登録・認証
        self.add_route('/v1/Users', issuers.Collection())
        self.add_route('/v1/Users/{user_id}', issuers.Item())

        # コントラクトテンプレート登録・コンパイル、参照
        self.add_route('/v1/TokenTemplate', tokenTemplates.SetTemplate())
        self.add_route('/v1/TokenTemplates', tokenTemplates.GetAll())
        self.add_route('/v1/TokenTemplates/{contract_id}', tokenTemplates.GetContractABI())

        # トークン一覧
        self.add_route('/v1/Contracts', contracts.Contracts())

        # 保有トークン一覧
        self.add_route('/v1/MyTokens', position.MyTokens())

        self.add_error_handler(AppError, AppError.handle)

init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
