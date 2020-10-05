# -*- coding: utf-8 -*-
import falcon

from app import log
from app.middleware import JSONTranslator, DatabaseSessionManager
from app.database import db_session, init_session

from app.api.common import base
from app.api.v2 import admin
from app.api.v2 import token_abi, notification, eth, company, user, nodeInfo, \
    token, market_information, position, order_list, statistics


from app.errors import AppError

LOG = log.get_logger()


class App(falcon.API):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())

        """
        Version 2
        """

        # 管理者向け
        self.add_route('/v2/Admin/Tokens', admin.Tokens())
        self.add_route('/v2/Admin/Tokens/Type', admin.TokenType())
        self.add_route('/v2/Admin/Token/{contract_address}', admin.Token())

        # トランザクション
        self.add_route('/v2/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())
        self.add_route('/v2/Eth/SendRawTransaction', eth.SendRawTransaction())
        self.add_route('/v2/Eth/SendRawTransactionNoWait', eth.SendRawTransactionNoWait())

        # 会社情報
        self.add_route('/v2/Company/{eth_address}', company.CompanyInfo())
        self.add_route('/v2/Companies', company.CompanyInfoList())
        self.add_route('/v2/Company/{eth_address}/Tokens', company.CompanyTokenList())
        self.add_route('/v2/PaymentAgent/{eth_address}', company.PaymentAgentInfo())

        # トークンABI参照
        self.add_route('/v2/ABI/StraightBond', token_abi.StraightBondABI())
        self.add_route('/v2/ABI/Share', token_abi.ShareABI())
        self.add_route('/v2/ABI/Membership', token_abi.MembershipABI())
        self.add_route('/v2/ABI/Coupon', token_abi.CouponABI())

        # トークン一覧参照
        self.add_route('/v2/Token/StraightBond', token.StraightBondTokens())
        self.add_route('/v2/Token/StraightBond/Address', token.StraightBondTokenAddresses())
        self.add_route('/v2/Token/Share', token.ShareTokens())
        self.add_route('/v2/Token/Share/Address', token.ShareTokenAddresses())
        self.add_route('/v2/Token/Membership', token.MembershipTokens())
        self.add_route('/v2/Token/Membership/Address', token.MembershipTokenAddresses())
        self.add_route('/v2/Token/Coupon', token.CouponTokens())
        self.add_route('/v2/Token/Coupon/Address', token.CouponTokenAddresses())

        # トークン詳細参照
        self.add_route('/v2/Token/StraightBond/{contract_address}', token.StraightBondTokenDetails())
        self.add_route('/v2/Token/Share/{contract_address}', token.ShareTokenDetails())
        self.add_route('/v2/Token/Membership/{contract_address}', token.MembershipTokenDetails())
        self.add_route('/v2/Token/Coupon/{contract_address}', token.CouponTokenDetails())

        # トークン取扱ステータス参照
        self.add_route('/v2/Token/{contract_address}/Status', token.TokenStatus())

        # トークン保有者一覧参照
        self.add_route('/v2/Token/{contract_address}/Holders', token.TokenHolders())

        # トークン移転履歴
        self.add_route('/v2/Token/{contract_address}/TransferHistory', token.TransferHistory())

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
        self.add_route('/v2/Position/StraightBond', position.StraightBondMyTokens())
        self.add_route('/v2/Position/Share', position.ShareMyTokens())
        self.add_route('/v2/Position/Membership', position.MembershipMyTokens())
        self.add_route('/v2/Position/Coupon', position.CouponMyTokens())
        self.add_route('/v2/Position/Coupon/Consumptions', position.CouponConsumptions())

        # 注文一覧・約定一覧
        self.add_route('/v2/OrderList/StraightBond', order_list.StraightBondOrderList())
        self.add_route('/v2/OrderList/Share', order_list.ShareOrderList())
        self.add_route('/v2/OrderList/Membership', order_list.MembershipOrderList())
        self.add_route('/v2/OrderList/Coupon', order_list.CouponOrderList())

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

        # 統計値
        self.add_route('/v2/Statistics/Token/{contract_address}', statistics.Token())

        """
        Error Handler
        """

        self.add_error_handler(AppError, AppError.handle)


init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session)]
application = App(middleware=middleware)
