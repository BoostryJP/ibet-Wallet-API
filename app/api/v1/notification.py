# -*- coding: utf-8 -*-
import json
import requests
import os
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=+9), 'JST')

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import TokenTemplate
from app.errors import AppError, InvalidParameterError
from app import config

LOG = log.get_logger()

# ------------------------------
# 通知一覧
# ------------------------------
class Notifications(BaseResource):
    '''
    Handle for endpoint: /v1/Notifications/
    '''
    def on_post(self, req, res):
        LOG.info('v1.Notification.Notifications')
        session = req.context['session']

        request_json = Notifications.validate(req)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        if config.WEB3_CHAINID == '4' or '2017':
            from web3.middleware import geth_poa_middleware
            web3.middleware_stack.inject(geth_poa_middleware, layer=0)

        # Exchange Contract
        exchange_contract_address = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        exchange_contract_abi = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)
        ExchangeContract = web3.eth.contract(
            address = to_checksum_address(exchange_contract_address),
            abi = exchange_contract_abi,
        )

        # WhiteList Contract
        whitelist_contract_address = os.environ.get('WHITE_LIST_CONTRACT_ADDRESS')
        whitelist_contract_abi = json.loads(config.WHITE_LIST_CONTRACT_ABI)
        WhiteListContract = web3.eth.contract(
            address = to_checksum_address(whitelist_contract_address),
            abi = whitelist_contract_abi,
        )

        # TokenList Contract
        list_contract_address = config.TOKEN_LIST_CONTRACT_ADDRESS
        list_contract_abi = json.loads(config.TOKEN_LIST_CONTRACT_ABI)
        ListContract = web3.eth.contract(
            address = to_checksum_address(list_contract_address),
            abi = list_contract_abi,
        )

        try:
            company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            company_list = []

        notifications = []
        for account_address in request_json['account_address_list']:
            # イベント：決済用口座登録
            event_filter = WhiteListContract.eventFilter(
                'Register', {
                    'filter':{'account_address':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'WhiteListRegister',
                    'args':dict(entry['args'])
                })

            # イベント：決済用口座情報更新
            event_filter = WhiteListContract.eventFilter(
                'ChangeInfo', {
                    'filter':{'account_address':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'WhiteListChangeInfo',
                    'args':dict(entry['args'])
                })

            # イベント：決済用口座承認
            event_filter = WhiteListContract.eventFilter(
                'Approve', {
                    'filter':{'account_address':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'WhiteListApprove',
                    'args':dict(entry['args'])
                })

            # イベント：決済用口座警告
            event_filter = WhiteListContract.eventFilter(
                'Warn', {
                    'filter':{'account_address':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'WhiteListWarn',
                    'args':dict(entry['args'])
                })

            # イベント：決済用口座非承認・凍結
            event_filter = WhiteListContract.eventFilter(
                'Unapprove', {
                    'filter':{'account_address':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'WhiteListUnapprove',
                    'args':dict(entry['args'])
                })

            # イベント：注文
            event_filter = ExchangeContract.eventFilter(
                'NewOrder', {
                    'filter':{'accountAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'NewOrder',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：注文取消
            event_filter = ExchangeContract.eventFilter(
                'CancelOrder', {
                    'filter':{'accountAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'CancelOrder',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：約定（買）
            event_filter = ExchangeContract.eventFilter(
                'Agree', {
                    'filter':{'buyAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'BuyAgreement',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：約定（売）
            event_filter = ExchangeContract.eventFilter(
                'Agree', {
                    'filter':{'sellAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'SellAgreement',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：決済OK（買）
            event_filter = ExchangeContract.eventFilter(
                'SettlementOK', {
                    'filter':{'buyAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'BuySettlementOK',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：決済OK（売）
            event_filter = ExchangeContract.eventFilter(
                'SettlementOK', {
                    'filter':{'sellAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'SellSettlementOK',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：決済NG（買）
            event_filter = ExchangeContract.eventFilter(
                'SettlementNG', {
                    'filter':{'buyAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'BuySettlementNG',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

            # イベント：決済NG（売）
            event_filter = ExchangeContract.eventFilter(
                'SettlementNG', {
                    'filter':{'sellAddress':to_checksum_address(account_address)},
                    'fromBlock':request_json['from']['block_number']
                }
            )
            entries = event_filter.get_all_entries()
            for entry in entries:
                token_address = to_checksum_address(entry['args']['tokenAddress'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )
                token_name = TokenContract.functions.name().call()
                owner_address = TokenContract.functions.owner().call()

                company_name = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']

                notifications.append({
                    'block_timestamp':datetime.fromtimestamp(web3.eth.getBlock(entry['blockNumber'])['timestamp'], JST).strftime("%Y/%m/%d %H:%M:%S"),
                    'block_number':entry['blockNumber'],
                    'transaction_hash':web3.toHex(entry['transactionHash']),
                    'notification_type':'SellSettlementNG',
                    'token_name': token_name,
                    'company_name': company_name,
                    'args':dict(entry['args'])
                })

        # blockNumber => transactionHash でソート
        notifications = sorted(notifications, key=lambda x: (x['block_number'],x['transaction_hash']))

        response_list_tmp = []
        for item in notifications:
            if request_json['from']['block_number'] == item['block_number'] and \
                request_json['from']['transaction_hash'] < item['transaction_hash']:
                response_list_tmp.append(item)
            elif request_json['from']['block_number'] < item['block_number']:
                response_list_tmp.append(item)

        max_size = len(response_list_tmp)
        if max_size == 0:
            response_list = []
            latest_block_number = request_json['from']['block_number']
            latest_transaction_hash = request_json['from']['transaction_hash']
            has_next = False
        elif max_size > request_json['size']:
            list_size = request_json['size']
            response_list = response_list_tmp[0:list_size]
            latest_block_number = response_list[list_size-1]['block_number']
            latest_transaction_hash = response_list[list_size-1]['transaction_hash']
            has_next = True
        else:
            response_list = response_list_tmp
            latest_block_number = response_list[max_size-1]['block_number']
            latest_transaction_hash = response_list[max_size-1]['transaction_hash']
            has_next = False

        response_json = {
            'notifications': response_list,
            'latest_block_number': latest_block_number,
            'latest_transaction_hash': latest_transaction_hash,
            'has_next': has_next
        }

        self.on_success(res, response_json)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'account_address_list': {
                'type': 'list',
                'schema': {'type': 'string'},
                'empty': False,
                'required': True
            },
            'from': {
                'type': 'dict',
                'schema': {
                    'block_number':{'type':'integer','empty': False,'required': True, 'min':0},
                    'transaction_hash':{'type':'string','empty': False,'required': True}
                },
                'empty': False,
                'required': True
            },
            'size': {
                'type':'integer',
                'min':0,
                'empty': False,
                'required': True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json['account_address_list']:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json
