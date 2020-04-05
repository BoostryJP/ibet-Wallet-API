# -*- coding: utf-8 -*-
import falcon

from app import log
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session

from app.api.common import base
from app.api.common import eth
from app.api.common import company
from app.api.common import notification
from app.api.common import user
from app.api.common import push
from app.api.common import version
from app.api.common import nodeInfo

from app.api.payment import stripe

from app.api.v1 import tokenTemplates
from app.api.v1 import contracts
from app.api.v1 import marketInformation
from app.api.v1 import position
from app.api.v1 import orderList

from app.api.v2 import token_abi
from app.api.v2 import token
from app.api.v2 import market_information
from app.api.v2 import position as v2position
from app.api.v2 import order_list
from app.api.v2 import statistics


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

        # 受領用銀行口座登録状況参照
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

        # トランザクション
        self.add_route('/v2/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())
        self.add_route('/v2/Eth/SendRawTransaction', eth.SendRawTransaction())
        self.add_route('/v2/Eth/SendRawTransactionNoWait', eth.SendRawTransactionNoWait())

        # 会社情報
        self.add_route('/v2/Company/{eth_address}', company.CompanyInfo())
        self.add_route('/v2/Companies', company.CompanyInfoList())
        self.add_route('/v2/PaymentAgent/{eth_address}', company.PaymentAgentInfo())

        # トークンABI参照
        self.add_route('/v2/ABI/StraightBond', token_abi.StraightBondABI())
        self.add_route('/v2/ABI/Membership', token_abi.MembershipABI())
        self.add_route('/v2/ABI/Coupon', token_abi.CouponABI())

        # トークン一覧参照
        self.add_route('/v2/Token/StraightBond', token.StraightBondTokens())
        self.add_route('/v2/Token/Membership', token.MembershipTokens())
        self.add_route('/v2/Token/Coupon', token.CouponTokens())

        # トークン詳細参照
        self.add_route('/v2/Token/StraightBond/{contract_address}', token.StraightBondTokenDetails())
        self.add_route('/v2/Token/Membership/{contract_address}', token.MembershipTokenDetails())
        self.add_route('/v2/Token/Coupon/{contract_address}', token.CouponTokenDetails())

        # マーケット情報：オーダーブック
        self.add_route('/v2/Market/OrderBook/StraightBond', market_information.StraightBondOrderBook())
        self.add_route('/v2/Market/OrderBook/Membership', market_information.MembershipOrderBook())
        self.add_route('/v2/Market/OrderBook/Coupon', market_information.CouponOrderBook())

        # マーケット情報：現在値
        self.add_route('/v2/Market/LastPrice/StraightBond', market_information.StraightBondLastPrice())
        self.add_route('/v2/Market/LastPrice/Membership', market_information.MembershipLastPrice())
        self.add_route('/v2/Market/LastPrice/Coupon', market_information.CouponLastPrice())

        # マーケット情報：歩み値
        self.add_route('/v2/Market/Tick/StraightBond', market_information.StraightBondTick())
        self.add_route('/v2/Market/Tick/Membership', market_information.MembershipTick())
        self.add_route('/v2/Market/Tick/Coupon', market_information.CouponTick())

        # マーケット情報：約定情報参照
        self.add_route('/v2/Market/Agreement', market_information.GetAgreement())

        # 保有トークン一覧
        self.add_route('/v2/Position/StraightBond', v2position.StraightBondMyTokens())
        self.add_route('/v2/Position/Membership', v2position.MembershipMyTokens())
        self.add_route('/v2/Position/Coupon', v2position.CouponMyTokens())
        self.add_route('/v2/Position/Coupon/Consumptions', v2position.CouponConsumptions())

        # 注文一覧・約定一覧
        self.add_route('/v2/OrderList', order_list.OrderList())

        # 通知一覧
        self.add_route('/v2/Notifications', notification.Notifications())
        self.add_route('/v2/Notifications/Read', notification.NotificationsRead())
        self.add_route('/v2/NotificationCount', notification.NotificationCount())

        # 受領用銀行口座登録状況参照
        self.add_route('/v2/User/PaymentAccount', user.PaymentAccount())

        # 名簿用個人情報参照
        self.add_route('/v2/User/PersonalInfo', user.PersonalInfo())

        # 住所検索（郵便番号）
        self.add_route('/v2/User/StreetAddress/{postal_code}', user.StreetAddress())

        # ノード情報
        self.add_route('/v2/NodeInfo', nodeInfo.NodeInfo())

        # push通知デバイス登録
        self.add_route('/v2/Push/UpdateDevice', push.UpdateDevice())
        self.add_route('/v2/Push/DeleteDevice', push.DeleteDevice())

        # 動作保証アプリバーションの取得
        self.add_route('/v2/RequiredVersion', version.RequiredVersion())

        # Stripe決済
        self.add_route('/v2/Stripe/CreateAccount', stripe.CreateAccount())
        self.add_route('/v2/Stripe/CreateExternalAccount', stripe.CreateExternalAccount())
        self.add_route('/v2/Stripe/CreateCustomer', stripe.CreateCustomer())
        self.add_route('/v2/Stripe/DeleteAccount', stripe.DeleteAccount())
        self.add_route('/v2/Stripe/Charge', stripe.Charge())
        self.add_route('/v2/Stripe/AccountStatus', stripe.AccountStatus())
        self.add_route('/v2/Stripe/ChargeStatus', stripe.ChargeStatus())
        self.add_route('/v2/Stripe/Constants', stripe.Constants())

        # 統計値
        self.add_route('/v2/Statistics/Token/{contract_address}', statistics.Token())

        """
        Error Handler
        """

        self.add_error_handler(AppError, AppError.handle)


init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
