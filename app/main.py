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

import falcon

from app import log
from app.middleware import JSONTranslator, DatabaseSessionManager, CORSMiddleware
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

        # System Environment Settings
        self.add_route('/v2/Admin/Tokens', admin.Tokens())
        self.add_route('/v2/Admin/Tokens/Type', admin.TokenType())
        self.add_route('/v2/Admin/Token/{contract_address}', admin.Token())

        # Blockchain Transactions
        self.add_route('/v2/Eth/TransactionCount/{eth_address}', eth.GetTransactionCount())
        self.add_route('/v2/Eth/SendRawTransaction', eth.SendRawTransaction())
        self.add_route('/v2/Eth/SendRawTransactionNoWait', eth.SendRawTransactionNoWait())
        self.add_route('/v2/Eth/WaitForTransactionReceipt', eth.WaitForTransactionReceipt())

        # Blockchain Node Information
        self.add_route('/v2/NodeInfo', nodeInfo.NodeInfo())
        self.add_route('/v2/NodeInfo/BlockSyncStatus', nodeInfo.BlockSyncStatus())

        # Contract ABIs
        self.add_route('/v2/ABI/StraightBond', token_abi.StraightBondABI())
        self.add_route('/v2/ABI/Share', token_abi.ShareABI())
        self.add_route('/v2/ABI/Membership', token_abi.MembershipABI())
        self.add_route('/v2/ABI/Coupon', token_abi.CouponABI())

        # Companies
        self.add_route('/v2/Company/{eth_address}', company.CompanyInfo())
        self.add_route('/v2/Companies', company.CompanyInfoList())
        self.add_route('/v2/Company/{eth_address}/Tokens', company.CompanyTokenList())
        self.add_route('/v2/PaymentAgent/{eth_address}', company.PaymentAgentInfo())

        # Tokens
        self.add_route('/v2/Token/StraightBond', token.StraightBondTokens())
        self.add_route('/v2/Token/StraightBond/Address', token.StraightBondTokenAddresses())
        self.add_route('/v2/Token/StraightBond/{contract_address}', token.StraightBondTokenDetails())
        self.add_route('/v2/Token/Share', token.ShareTokens())
        self.add_route('/v2/Token/Share/Address', token.ShareTokenAddresses())
        self.add_route('/v2/Token/Share/{contract_address}', token.ShareTokenDetails())
        self.add_route('/v2/Token/Membership', token.MembershipTokens())
        self.add_route('/v2/Token/Membership/Address', token.MembershipTokenAddresses())
        self.add_route('/v2/Token/Membership/{contract_address}', token.MembershipTokenDetails())
        self.add_route('/v2/Token/Coupon', token.CouponTokens())
        self.add_route('/v2/Token/Coupon/Address', token.CouponTokenAddresses())
        self.add_route('/v2/Token/Coupon/{contract_address}', token.CouponTokenDetails())
        self.add_route('/v2/Token/{contract_address}/Status', token.TokenStatus())
        self.add_route('/v2/Token/{contract_address}/Holders', token.TokenHolders())
        self.add_route('/v2/Token/{contract_address}/TransferHistory', token.TransferHistory())
        self.add_route('/v2/Token/{contract_address}/TransferApprovalHistory', token.TransferApprovalHistory())

        # Market Data
        self.add_route('/v2/Market/OrderBook/StraightBond', market_information.StraightBondOrderBook())
        self.add_route('/v2/Market/OrderBook/Membership', market_information.MembershipOrderBook())
        self.add_route('/v2/Market/OrderBook/Coupon', market_information.CouponOrderBook())
        self.add_route('/v2/Market/LastPrice/StraightBond', market_information.StraightBondLastPrice())
        self.add_route('/v2/Market/LastPrice/Membership', market_information.MembershipLastPrice())
        self.add_route('/v2/Market/LastPrice/Coupon', market_information.CouponLastPrice())
        self.add_route('/v2/Market/Tick/StraightBond', market_information.StraightBondTick())
        self.add_route('/v2/Market/Tick/Membership', market_information.MembershipTick())
        self.add_route('/v2/Market/Tick/Coupon', market_information.CouponTick())
        self.add_route('/v2/Market/Agreement', market_information.GetAgreement())

        # Position
        self.add_route('/v2/Position/StraightBond', position.StraightBondMyTokens())
        self.add_route('/v2/Position/Share', position.ShareMyTokens())
        self.add_route('/v2/Position/Membership', position.MembershipMyTokens())
        self.add_route('/v2/Position/Coupon', position.CouponMyTokens())
        self.add_route('/v2/Position/Coupon/Consumptions', position.CouponConsumptions())

        # Orders
        self.add_route('/v2/OrderList/{token_address}', order_list.OrderList())
        self.add_route('/v2/OrderList/StraightBond', order_list.StraightBondOrderList())
        self.add_route('/v2/OrderList/Share', order_list.ShareOrderList())
        self.add_route('/v2/OrderList/Membership', order_list.MembershipOrderList())
        self.add_route('/v2/OrderList/Coupon', order_list.CouponOrderList())

        # Notifications
        self.add_route('/v2/Notifications', notification.Notifications())
        self.add_route('/v2/Notifications/Read', notification.NotificationsRead())
        self.add_route('/v2/NotificationCount', notification.NotificationCount())

        # User Information
        self.add_route('/v2/User/PaymentAccount', user.PaymentAccount())
        self.add_route('/v2/User/PersonalInfo', user.PersonalInfo())

        # Statistics
        self.add_route('/v2/Statistics/Token/{contract_address}', statistics.Token())

        """
        Error Handler
        """

        self.add_error_handler(AppError, AppError.handle)


init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session), CORSMiddleware()]
application = App(middleware=middleware)

LOG.info("Service started successfully")
