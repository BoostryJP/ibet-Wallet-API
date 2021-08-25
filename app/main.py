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
from app.middleware import (
    JSONTranslator,
    DatabaseSessionManager,
    CORSMiddleware
)
from app.database import (
    db_session,
    init_session
)

from app.api.common import base
from app.api.v2 import (
    admin as v2_admin,
    token_abi as v2_token_abi,
    notification as v2_notification,
    eth as v2_eth,
    company as v2_company,
    user as v2_user,
    nodeInfo as v2_nodeInfo,
    token as v2_token,
    market_information as v2_market_information,
    position as v2_position,
    order_list as v2_order_list,
    statistics as v2_statistics
)
from app.api.v3 import (
    notification as v3_notification,
    position as v3_position,
    e2e_message
)

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
        self.add_route('/v2/Admin/Tokens', v2_admin.Tokens())
        self.add_route('/v2/Admin/Tokens/Type', v2_admin.TokenType())
        self.add_route('/v2/Admin/Token/{contract_address}', v2_admin.Token())

        # Blockchain Transactions
        self.add_route('/v2/Eth/TransactionCount/{eth_address}', v2_eth.GetTransactionCount())
        self.add_route('/v2/Eth/SendRawTransaction', v2_eth.SendRawTransaction())
        self.add_route('/v2/Eth/SendRawTransactionNoWait', v2_eth.SendRawTransactionNoWait())
        self.add_route('/v2/Eth/WaitForTransactionReceipt', v2_eth.WaitForTransactionReceipt())

        # Blockchain Node Information
        self.add_route('/v2/NodeInfo', v2_nodeInfo.NodeInfo())
        self.add_route('/v2/NodeInfo/BlockSyncStatus', v2_nodeInfo.BlockSyncStatus())

        # Contract ABIs
        self.add_route('/v2/ABI/StraightBond', v2_token_abi.StraightBondABI())
        self.add_route('/v2/ABI/Share', v2_token_abi.ShareABI())
        self.add_route('/v2/ABI/Membership', v2_token_abi.MembershipABI())
        self.add_route('/v2/ABI/Coupon', v2_token_abi.CouponABI())

        # Companies
        self.add_route('/v2/Company/{eth_address}', v2_company.CompanyInfo())
        self.add_route('/v2/Companies', v2_company.CompanyInfoList())
        self.add_route('/v2/Company/{eth_address}/Tokens', v2_company.CompanyTokenList())

        # Tokens
        self.add_route('/v2/Token/StraightBond', v2_token.StraightBondTokens())
        self.add_route('/v2/Token/StraightBond/Address', v2_token.StraightBondTokenAddresses())
        self.add_route('/v2/Token/StraightBond/{contract_address}', v2_token.StraightBondTokenDetails())
        self.add_route('/v2/Token/Share', v2_token.ShareTokens())
        self.add_route('/v2/Token/Share/Address', v2_token.ShareTokenAddresses())
        self.add_route('/v2/Token/Share/{contract_address}', v2_token.ShareTokenDetails())
        self.add_route('/v2/Token/Membership', v2_token.MembershipTokens())
        self.add_route('/v2/Token/Membership/Address', v2_token.MembershipTokenAddresses())
        self.add_route('/v2/Token/Membership/{contract_address}', v2_token.MembershipTokenDetails())
        self.add_route('/v2/Token/Coupon', v2_token.CouponTokens())
        self.add_route('/v2/Token/Coupon/Address', v2_token.CouponTokenAddresses())
        self.add_route('/v2/Token/Coupon/{contract_address}', v2_token.CouponTokenDetails())
        self.add_route('/v2/Token/{contract_address}/Status', v2_token.TokenStatus())
        self.add_route('/v2/Token/{contract_address}/Holders', v2_token.TokenHolders())
        self.add_route('/v2/Token/{contract_address}/TransferHistory', v2_token.TransferHistory())
        self.add_route('/v2/Token/{contract_address}/TransferApprovalHistory', v2_token.TransferApprovalHistory())

        # Market Data
        self.add_route('/v2/Market/OrderBook/StraightBond', v2_market_information.StraightBondOrderBook())
        self.add_route('/v2/Market/OrderBook/Membership', v2_market_information.MembershipOrderBook())
        self.add_route('/v2/Market/OrderBook/Coupon', v2_market_information.CouponOrderBook())
        self.add_route('/v2/Market/LastPrice/StraightBond', v2_market_information.StraightBondLastPrice())
        self.add_route('/v2/Market/LastPrice/Membership', v2_market_information.MembershipLastPrice())
        self.add_route('/v2/Market/LastPrice/Coupon', v2_market_information.CouponLastPrice())
        self.add_route('/v2/Market/Tick/StraightBond', v2_market_information.StraightBondTick())
        self.add_route('/v2/Market/Tick/Membership', v2_market_information.MembershipTick())
        self.add_route('/v2/Market/Tick/Coupon', v2_market_information.CouponTick())
        self.add_route('/v2/Market/Agreement', v2_market_information.GetAgreement())

        # Position
        self.add_route('/v2/Position/StraightBond', v2_position.StraightBondMyTokens())
        self.add_route('/v2/Position/Share', v2_position.ShareMyTokens())
        self.add_route('/v2/Position/Membership', v2_position.MembershipMyTokens())
        self.add_route('/v2/Position/Coupon', v2_position.CouponMyTokens())
        self.add_route('/v2/Position/Coupon/Consumptions', v2_position.CouponConsumptions())

        # Orders
        self.add_route('/v2/OrderList/{token_address}', v2_order_list.OrderList())
        self.add_route('/v2/OrderList/StraightBond', v2_order_list.StraightBondOrderList())
        self.add_route('/v2/OrderList/Share', v2_order_list.ShareOrderList())
        self.add_route('/v2/OrderList/Membership', v2_order_list.MembershipOrderList())
        self.add_route('/v2/OrderList/Coupon', v2_order_list.CouponOrderList())

        # Notifications
        self.add_route('/v2/Notifications', v2_notification.Notifications())
        self.add_route('/v2/Notifications/Read', v2_notification.NotificationsRead())
        self.add_route('/v2/NotificationCount', v2_notification.NotificationCount())

        # User Information
        self.add_route('/v2/User/PaymentAccount', v2_user.PaymentAccount())
        self.add_route('/v2/User/PersonalInfo', v2_user.PersonalInfo())

        # Statistics
        self.add_route('/v2/Statistics/Token/{contract_address}', v2_statistics.Token())

        """
        Version 3
        """

        # Position
        self.add_route('/v3/Position/{account_address}/Share', v3_position.PositionShare())
        self.add_route('/v3/Position/{account_address}/StraightBond', v3_position.PositionStraightBond())
        self.add_route('/v3/Position/{account_address}/Membership', v3_position.PositionMembership())
        self.add_route('/v3/Position/{account_address}/Coupon', v3_position.PositionCoupon())
        self.add_route('/v3/Position/{account_address}/Share/{contract_address}',
                       v3_position.PositionShareContractAddress())
        self.add_route('/v3/Position/{account_address}/StraightBond/{contract_address}',
                       v3_position.PositionStraightBondContractAddress())
        self.add_route('/v3/Position/{account_address}/Membership/{contract_address}',
                       v3_position.PositionMembershipContractAddress())
        self.add_route('/v3/Position/{account_address}/Coupon/{contract_address}',
                       v3_position.PositionCouponContractAddress())

        # Notifications
        self.add_route('/v3/Notifications', v3_notification.Notifications())
        self.add_route('/v3/Notifications/{id}', v3_notification.NotificationsId())

        # E2E Message
        self.add_route('/v3/E2EMessage/EncryptionKey/{account_address}', e2e_message.EncryptionKey())

        """
        Error Handler
        """

        self.add_error_handler(AppError, AppError.handle)


init_session()
middleware = [JSONTranslator(), DatabaseSessionManager(db_session), CORSMiddleware()]
application = App(middleware=middleware)

LOG.info("Service started successfully")
