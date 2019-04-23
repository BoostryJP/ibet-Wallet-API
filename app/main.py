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
from app.api.v1 import nodeInfo
from app.api.v1 import omise
from app.api.v1 import stripe
from app.api.v1 import push
from app.api.v1 import version

from app.errors import AppError

LOG = log.get_logger()

class App(falcon.API):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())

        # トランザクション
        self.add_route('/v1/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())
        self.add_route('/v1/Eth/SendRawTransaction', eth.SendRawTransaction())

        # トークンテンプレート
        self.add_route('/v1/StraightBondABI/', tokenTemplates.GetStraightBondABI())
        self.add_route('/v1/MembershipABI/', tokenTemplates.GetMembershipABI())
        self.add_route('/v1/CouponABI/', tokenTemplates.GetCouponABI())

        # 会社情報
        self.add_route('/v1/Company/{eth_address}', company.CompanyInfo())
        self.add_route('/v1/PaymentAgent/{eth_address}', company.PaymentAgentInfo())

        # マーケット情報：トークン一覧
        self.add_route('/v1/StraightBond/Contracts', contracts.Contracts())
        self.add_route('/v1/Membership/Contracts', contracts.MembershipContracts())
        self.add_route('/v1/Coupon/Contracts', contracts.CouponContracts())

        # マーケット情報：オーダーブック
        self.add_route('/v1/StraightBond/OrderBook', marketInformation.OrderBook())
        self.add_route('/v1/Membership/OrderBook', marketInformation.MembershipOrderBook())
        self.add_route('/v1/Coupon/OrderBook', marketInformation.CouponOrderBook())

        # マーケット情報：現在値
        self.add_route('/v1/StraightBond/LastPrice', marketInformation.LastPrice())
        self.add_route('/v1/Membership/LastPrice', marketInformation.MembershipLastPrice())
        self.add_route('/v1/Coupon/LastPrice', marketInformation.CouponLastPrice())

        # マーケット情報：歩み値
        self.add_route('/v1/StraightBond/Tick', marketInformation.Tick())
        self.add_route('/v1/Membership/Tick', marketInformation.MembershipTick())
        self.add_route('/v1/Coupon/Tick', marketInformation.CouponTick())

        # 保有トークン一覧
        self.add_route('/v1/StraightBond/MyTokens', position.MyTokens())
        self.add_route('/v1/Membership/MyTokens', position.MembershipMyTokens())
        self.add_route('/v1/Coupon/MyTokens', position.CouponMyTokens())
        self.add_route('/v1/CouponConsumptions', position.CouponConsumptions())

        # 注文一覧・約定一覧
        self.add_route('/v1/OrderList', orderList.OrderList())

        # 通知一覧
        self.add_route('/v1/Notifications', notification.Notifications())
        self.add_route('/v1/Notifications/Read', notification.NotificationsRead())
        self.add_route('/v1/NotificationCount', notification.NotificationCount())

        # 決済用口座登録状況参照
        self.add_route('/v1/User/PaymentAccount', user.PaymentAccount())

        # 名簿用個人情報参照
        self.add_route('/v1/User/PersonalInfo', user.PersonalInfo())

        # ノード情報
        self.add_route('/v1/NodeInfo', nodeInfo.NodeInfo())

        # Omise決済
        self.add_route('/v1/Omise/CreateCustomer', omise.CreateCustomer())
        self.add_route('/v1/Omise/UpdateCustomer', omise.UpdateCustomer())
        self.add_route('/v1/Omise/Charge', omise.Charge())
        self.add_route('/v1/Omise/ChargeStatus', omise.ChargeStatus())

        # Stripe決済
        self.add_route('/v1/Stripe/CreateAccount/', stripe.CreateAccount())
        self.add_route('/v1/Stripe/CreateExternalAccount/', stripe.CreateExternalAccount())
        self.add_route('/v1/Stripe/GetAccountInfo/', stripe.GetAccountInfo())
        self.add_route('/v1/Stripe/CreateCustomer/', stripe.CreateCustomer())
        self.add_route('/v1/Stripe/Charge/', stripe.Charge())

        # push通知デバイス登録
        self.add_route('/v1/Push/UpdateDevice', push.UpdateDevice())
        self.add_route('/v1/Push/DeleteDevice', push.DeleteDevice())

        # 動作保証アプリバーションの取得
        self.add_route('/v1/RequiredVersion', version.RequiredVersion())

        self.add_error_handler(AppError, AppError.handle)

init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
