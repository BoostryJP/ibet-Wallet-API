# -*- coding: utf-8 -*-
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
from app.api.v1 import stripe
from app.api.v1 import push
from app.api.v1 import version

from app.api.v2 import token_abi
from app.api.v2 import token
from app.api.v2 import market_information

from app.errors import AppError

LOG = log.get_logger()


class App(falcon.API):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())

        """
        Version 1
        """

        # トランザクション
        self.add_route('/v1/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())
        self.add_route('/v1/Eth/SendRawTransaction', eth.SendRawTransaction())

        # トークンテンプレート
        self.add_route('/v1/StraightBondABI/', tokenTemplates.GetStraightBondABI())
        self.add_route('/v1/MembershipABI/', tokenTemplates.GetMembershipABI())
        self.add_route('/v1/CouponABI/', tokenTemplates.GetCouponABI())
        self.add_route('/v1/MRFABI/', tokenTemplates.GetMRFABI())
        self.add_route('/v1/JDRABI/', tokenTemplates.GetJDRABI())

        # 会社情報
        self.add_route('/v1/Company/{eth_address}', company.CompanyInfo())
        self.add_route('/v1/PaymentAgent/{eth_address}', company.PaymentAgentInfo())

        # マーケット情報：トークン一覧
        self.add_route('/v1/JDR/Contracts', contracts.JDRContracts())
        self.add_route('/v1/MRF/Contracts', contracts.MRFContracts())
        self.add_route('/v1/StraightBond/Contracts', contracts.Contracts())
        self.add_route('/v1/Membership/Contracts', contracts.MembershipContracts())
        self.add_route('/v1/Coupon/Contracts', contracts.CouponContracts())

        # マーケット情報：オーダーブック
        self.add_route('/v1/StraightBond/OrderBook', marketInformation.OrderBook())
        self.add_route('/v1/Membership/OrderBook', marketInformation.MembershipOrderBook())
        self.add_route('/v1/Coupon/OrderBook', marketInformation.CouponOrderBook())

        # マーケット情報：現在値
        self.add_route('/v1/JDR/LastPrice', marketInformation.JDRLastPrice())
        self.add_route('/v1/StraightBond/LastPrice', marketInformation.LastPrice())
        self.add_route('/v1/Membership/LastPrice', marketInformation.MembershipLastPrice())
        self.add_route('/v1/Coupon/LastPrice', marketInformation.CouponLastPrice())

        # マーケット情報：歩み値
        self.add_route('/v1/JDR/Tick', marketInformation.JDRTick())
        self.add_route('/v1/StraightBond/Tick', marketInformation.Tick())
        self.add_route('/v1/Membership/Tick', marketInformation.MembershipTick())
        self.add_route('/v1/Coupon/Tick', marketInformation.CouponTick())

        # 保有トークン一覧
        self.add_route('/v1/JDR/MyTokens', position.JDRMyTokens())
        self.add_route('/v1/StraightBond/MyTokens', position.MyTokens())
        self.add_route('/v1/Membership/MyTokens', position.MembershipMyTokens())
        self.add_route('/v1/Coupon/MyTokens', position.CouponMyTokens())
        self.add_route('/v1/CouponConsumptions', position.CouponConsumptions())

        # 保有トークン一覧（決済用）
        self.add_route('/v1/MRF/MyTokens', position.MRFMyTokens())
        self.add_route('/v1/MRF/Transfers', position.MRFTransfers())

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

        # 住所検索（郵便番号）
        self.add_route('/v1/User/StreetAddress/{postal_code}', user.StreetAddress())

        # ノード情報
        self.add_route('/v1/NodeInfo', nodeInfo.NodeInfo())

        # Stripe決済
        self.add_route('/v1/Stripe/CreateAccount', stripe.CreateAccount())
        self.add_route('/v1/Stripe/CreateExternalAccount', stripe.CreateExternalAccount())
        self.add_route('/v1/Stripe/CreateCustomer', stripe.CreateCustomer())
        self.add_route('/v1/Stripe/DeleteAccount', stripe.DeleteAccount())
        self.add_route('/v1/Stripe/Charge', stripe.Charge())
        self.add_route('/v1/Stripe/AccountStatus', stripe.AccountStatus())
        self.add_route('/v1/Stripe/ChargeStatus', stripe.ChargeStatus())
        self.add_route('/v1/Stripe/Constants', stripe.Constants())

        # push通知デバイス登録
        self.add_route('/v1/Push/UpdateDevice', push.UpdateDevice())
        self.add_route('/v1/Push/DeleteDevice', push.DeleteDevice())

        # 動作保証アプリバーションの取得
        self.add_route('/v1/RequiredVersion', version.RequiredVersion())


        """
        Version 2
        """

        # トークンABI参照
        self.add_route('/v2/ABI/Membership', token_abi.MembershipABI())
        self.add_route('/v2/ABI/Coupon', token_abi.CouponABI())

        # トークン一覧参照
        self.add_route('/v2/Token/Membership', token.MembershipTokens())
        self.add_route('/v2/Token/Coupon', token.CouponTokens())

        # マーケット情報：オーダーブック
        self.add_route('/v2/OrderBook/Membership', market_information.MembershipOrderBook())
        self.add_route('/v2/OrderBook/Coupon', market_information.CouponOrderBook())

        # マーケット情報：現在値
        self.add_route('/v2/LastPrice/Membership', market_information.MembershipLastPrice())
        self.add_route('/v2/LastPrice/Coupon', market_information.CouponLastPrice())

        # マーケット情報：歩み値
        self.add_route('/v2/Tick/Membership', market_information.MembershipTick())
        self.add_route('/v2/Tick/Coupon', market_information.CouponTick())


        """
        Error Handler
        """

        self.add_error_handler(AppError, AppError.handle)


init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
