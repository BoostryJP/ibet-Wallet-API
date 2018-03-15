# -*- coding: utf-8 -*-
import os

import falcon

from app import log
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session

from app.api.common import base
from app.api.v1 import eth
from app.api.v1 import company
from app.api.v1 import user
from app.api.v1 import tokenTemplates
from app.api.v1 import contracts
from app.api.v1 import marketInformation
from app.api.v1 import position
from app.api.v1 import orderList
from app.api.v1 import notification

from app.errors import AppError

LOG = log.get_logger()

class App(falcon.API):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())

        # Ethereum
        self.add_route('/v1/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())
        self.add_route('/v1/Eth/SendRawTransaction', eth.SendRawTransaction())

        # トークンテンプレート登録・参照
        self.add_route('/v1/TokenTemplate', tokenTemplates.SetTemplate())
        self.add_route('/v1/TokenTemplates', tokenTemplates.GetAll())
        self.add_route('/v1/TokenTemplates/{contract_id}', tokenTemplates.GetContractABI())

        # 会社情報参照
        self.add_route('/v1/Company/{eth_address}', company.CompanyInfo())

        # 公開中トークン一覧
        self.add_route('/v1/Contracts', contracts.Contracts())

        # 板情報
        self.add_route('/v1/OrderBook', marketInformation.OrderBook())

        # 現在値
        self.add_route('/v1/LastPrice', marketInformation.LastPrice())

        # 歩み値
        self.add_route('/v1/Tick', marketInformation.Tick())

        # 保有トークン一覧
        self.add_route('/v1/MyTokens', position.MyTokens())

        # 注文一覧・約定一覧
        self.add_route('/v1/OrderList', orderList.OrderList())

        # 通知一覧
        self.add_route('/v1/Notifications', notification.Notifications())

        # 決済用口座登録状況参照
        self.add_route('/v1/User/PaymentAccount', user.PaymentAccount())

        # 名簿用個人情報参照
        self.add_route('/v1/User/PersonalInfo', user.PersonalInfo())

        self.add_error_handler(AppError, AppError.handle)

init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
