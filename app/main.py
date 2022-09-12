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
    CORSMiddleware,
    ResponseLoggerMiddleware
)
from app.database import (
    db_session,
    init_session
)

from app.api.common import base
from app.api.routers import (
    admin as routers_admin,
    node_info as routers_node_info,
    contract_abi as routers_abi,
    company_info as routers_company_info,
    user_info as routers_user_info,
    eth as routers_eth,
    token as routers_token,
    token_bond as routers_token_bond,
    token_share as routers_token_share,
    token_membership as routers_token_membership,
    token_coupon as routers_token_coupon,
    position as routers_position,
    notification as routers_notification,
    e2e_message as routers_e2e_message,
    events as routers_events, 
    dex_market as routers_dex_market, 
    dex_order_list as routers_dex_order_list,
)

from app.errors import AppError

LOG = log.get_logger()


class App(falcon.App):
    def __init__(self, *args, **kwargs):
        super(App, self).__init__(*args, **kwargs)
        LOG.info('API Server is starting')

        self.add_route('/', base.BaseResource())

        """
        Routers
        """

        # System Administration
        self.add_route('/Admin/Tokens', routers_admin.Tokens())
        self.add_route('/Admin/Tokens/Type', routers_admin.TokenType())
        self.add_route('/Admin/Tokens/{contract_address}', routers_admin.Token())

        # Blockchain Node Information
        self.add_route('/NodeInfo', routers_node_info.NodeInfo())
        self.add_route('/NodeInfo/BlockSyncStatus', routers_node_info.BlockSyncStatus())

        # Contract ABIs
        self.add_route('/ABI/StraightBond', routers_abi.StraightBondABI())
        self.add_route('/ABI/Share', routers_abi.ShareABI())
        self.add_route('/ABI/Membership', routers_abi.MembershipABI())
        self.add_route('/ABI/Coupon', routers_abi.CouponABI())

        # Company Information
        self.add_route('/Companies', routers_company_info.CompanyInfoList())
        self.add_route('/Companies/{eth_address}', routers_company_info.CompanyInfo())
        self.add_route('/Companies/{eth_address}/Tokens', routers_company_info.CompanyTokenList())

        # User Information
        self.add_route('/User/PaymentAccount', routers_user_info.PaymentAccount())
        self.add_route('/User/PersonalInfo', routers_user_info.PersonalInfo())

        # Blockchain Transactions
        self.add_route('/Eth/TransactionCount/{eth_address}', routers_eth.GetTransactionCount())
        self.add_route('/Eth/SendRawTransaction', routers_eth.SendRawTransaction())
        self.add_route('/Eth/SendRawTransactionNoWait', routers_eth.SendRawTransactionNoWait())
        self.add_route('/Eth/WaitForTransactionReceipt', routers_eth.WaitForTransactionReceipt())

        # Token
        self.add_route('/Token/StraightBond', routers_token_bond.StraightBondTokens())
        self.add_route('/Token/StraightBond/Addresses', routers_token_bond.StraightBondTokenAddresses())
        self.add_route('/Token/StraightBond/{contract_address}', routers_token_bond.StraightBondTokenDetails())
        self.add_route('/Token/Share', routers_token_share.ShareTokens())
        self.add_route('/Token/Share/Addresses', routers_token_share.ShareTokenAddresses())
        self.add_route('/Token/Share/{contract_address}', routers_token_share.ShareTokenDetails())
        self.add_route('/Token/Membership', routers_token_membership.MembershipTokens())
        self.add_route('/Token/Membership/Addresses', routers_token_membership.MembershipTokenAddresses())
        self.add_route('/Token/Membership/{contract_address}', routers_token_membership.MembershipTokenDetails())
        self.add_route('/Token/Coupon', routers_token_coupon.CouponTokens())
        self.add_route('/Token/Coupon/Addresses', routers_token_coupon.CouponTokenAddresses())
        self.add_route('/Token/Coupon/{contract_address}', routers_token_coupon.CouponTokenDetails())
        self.add_route('/Token/{contract_address}/Status', routers_token.TokenStatus())
        self.add_route('/Token/{contract_address}/Holders', routers_token.TokenHolders())
        self.add_route('/Token/{contract_address}/Holders/Count', routers_token.TokenHoldersCount())
        self.add_route('/Token/{contract_address}/Holders/Collection', routers_token.TokenHoldersCollection())
        self.add_route('/Token/{contract_address}/Holders/Collection/{list_id}', routers_token.TokenHoldersCollectionId())
        self.add_route('/Token/{contract_address}/TransferHistory', routers_token.TransferHistory())
        self.add_route('/Token/{contract_address}/TransferApprovalHistory', routers_token.TransferApprovalHistory())

        # Position
        self.add_route('/Position/{account_address}/StraightBond', routers_position.PositionStraightBond())
        self.add_route('/Position/{account_address}/StraightBond/{contract_address}', routers_position.PositionStraightBondContractAddress())
        self.add_route('/Position/{account_address}/Share', routers_position.PositionShare())
        self.add_route('/Position/{account_address}/Share/{contract_address}', routers_position.PositionShareContractAddress())
        self.add_route('/Position/{account_address}/Membership', routers_position.PositionMembership())
        self.add_route('/Position/{account_address}/Membership/{contract_address}', routers_position.PositionMembershipContractAddress())
        self.add_route('/Position/{account_address}/Coupon', routers_position.PositionCoupon())
        self.add_route('/Position/{account_address}/Coupon/{contract_address}', routers_position.PositionCouponContractAddress())

        # Notification
        self.add_route('/Notifications', routers_notification.Notifications())
        self.add_route('/Notifications/Read', routers_notification.NotificationsRead())
        self.add_route('/Notifications/Count', routers_notification.NotificationsCount())
        self.add_route('/Notifications/{id}', routers_notification.NotificationsId())

        # E2E Message
        self.add_route('/E2EMessage/EncryptionKey/{account_address}', routers_e2e_message.EncryptionKey())

        # Event Log
        self.add_route('/Events/E2EMessaging', routers_events.E2EMessagingEvents())
        self.add_route('/Events/IbetEscrow', routers_events.IbetEscrowEvents())
        self.add_route('/Events/IbetSecurityTokenEscrow', routers_events.IbetSecurityTokenEscrowEvents())

        # DEX Trade: Market Data
        self.add_route('/DEX/Market/OrderBook/StraightBond', routers_dex_market.StraightBondOrderBook())
        self.add_route('/DEX/Market/OrderBook/Membership', routers_dex_market.MembershipOrderBook())
        self.add_route('/DEX/Market/OrderBook/Coupon', routers_dex_market.CouponOrderBook())
        self.add_route('/DEX/Market/LastPrice/StraightBond', routers_dex_market.StraightBondLastPrice())
        self.add_route('/DEX/Market/LastPrice/Membership', routers_dex_market.MembershipLastPrice())
        self.add_route('/DEX/Market/LastPrice/Coupon', routers_dex_market.CouponLastPrice())
        self.add_route('/DEX/Market/Tick/StraightBond', routers_dex_market.StraightBondTick())
        self.add_route('/DEX/Market/Tick/Membership', routers_dex_market.MembershipTick())
        self.add_route('/DEX/Market/Tick/Coupon', routers_dex_market.CouponTick())
        self.add_route('/DEX/Market/Agreement', routers_dex_market.GetAgreement())

        # DEX Trade: Orders
        self.add_route('/DEX/OrderList/{token_address}', routers_dex_order_list.OrderList())
        self.add_route('/DEX/OrderList/StraightBond', routers_dex_order_list.StraightBondOrderList())
        self.add_route('/DEX/OrderList/Share', routers_dex_order_list.ShareOrderList())
        self.add_route('/DEX/OrderList/Membership', routers_dex_order_list.MembershipOrderList())
        self.add_route('/DEX/OrderList/Coupon', routers_dex_order_list.CouponOrderList())
        
        """
        Error Handler
        """

        self.add_error_handler(AppError, AppError.handle)


init_session()
middleware = [
    JSONTranslator(),
    DatabaseSessionManager(db_session),
    CORSMiddleware(),
    ResponseLoggerMiddleware()
]
application = App(middleware=middleware)
application.req_options.strip_url_path_trailing_slash = True

LOG.info("Service started successfully")
