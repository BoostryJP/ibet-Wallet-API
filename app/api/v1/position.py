# -*- coding: utf-8 -*-
import json
import requests
import os

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import TokenTemplate
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

# ------------------------------
# 保有トークン一覧
# ------------------------------
class MyTokens(BaseResource):
    '''
    Handle for endpoint: /v1/MyTokens/
    '''
    def on_post(self, req, res):
        LOG.info('v1.Position.MyTokens')
        session = req.context['session']

        request_json = MyTokens.validate(req)

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        # TokenList Contract
        list_contract_address = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')
        list_contract_abi = json.loads(config.TOKEN_LIST_CONTRACT_ABI)
        ListContract = web3.eth.contract(
            address = to_checksum_address(list_contract_address),
            abi = list_contract_abi,
        )

        try:
            company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            company_list = []

        # Exchange Contract
        exchange_contract_address = os.environ.get('IBET_SB_EXCHANGE_CONTRACT_ADDRESS')
        exchange_contract_abi = json.loads(config.IBET_EXCHANGE_CONTRACT_ABI)
        ExchangeContract = web3.eth.contract(
            address = to_checksum_address(exchange_contract_address),
            abi = exchange_contract_abi,
        )

        position_list = []
        for buy_address in request_json['account_address_list']:
            portfolio_list = []
            # 約定イベントから買い注文アドレスが一致するイベントを抽出する
            try:
                event_filter = ExchangeContract.eventFilter(
                    'Agree', {
                        'filter':{'buyAddress':to_checksum_address(buy_address)},
                        'fromBlock':'earliest'
                    }
                )
                entries = event_filter.get_all_entries()
                for entry in entries:
                    portfolio_list.append({
                        'account':entry['args']['buyAddress'],
                        'token_address':entry['args']['tokenAddress'],
                    })
            except:
                portfolio_list = []

            # リストをユニークにする
            portfolio_list_uniq = []
            for portfolio in portfolio_list:
                if portfolio not in portfolio_list_uniq :
                    portfolio_list_uniq.append(portfolio)

            # 残高（balance）、残注文（commitment）を取得する
            token_template = None
            for mytoken in portfolio_list_uniq:
                token_address = to_checksum_address(mytoken['token_address'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                if token_template[0] == '0x0000000000000000000000000000000000000000':
                    continue

                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template[1]).first().abi
                token_abi = json.loads(abi_str)
                TokenContract = web3.eth.contract(
                    address = token_address,
                    abi = token_abi
                )

                owner = to_checksum_address(mytoken['account'])
                balance = TokenContract.functions.balanceOf(owner).call()
                commitment = ExchangeContract.functions.commitments(owner,token_address).call()

                # 残高、残注文がゼロではない場合、Token-Contractから情報を取得する
                if balance == 0 and commitment == 0:
                    continue
                else:
                    name = TokenContract.functions.name().call()
                    symbol = TokenContract.functions.symbol().call()
                    totalSupply = TokenContract.functions.totalSupply().call()
                    faceValue = TokenContract.functions.faceValue().call()
                    interestRate = TokenContract.functions.interestRate().call()

                    interestPaymentDate_string = TokenContract.functions.interestPaymentDate().call()
                    interestPaymentDate = json.loads(
                        interestPaymentDate_string.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                    interestPaymentDate1 = ''
                    interestPaymentDate2 = ''
                    if 'interestPaymentDate1' in interestPaymentDate:
                        interestPaymentDate1 = interestPaymentDate['interestPaymentDate1']
                    if 'interestPaymentDate2' in interestPaymentDate:
                        interestPaymentDate2 = interestPaymentDate['interestPaymentDate2']

                    redemptionDate = TokenContract.functions.redemptionDate().call()
                    redemptionAmount = TokenContract.functions.redemptionAmount().call()
                    returnDate = TokenContract.functions.returnDate().call()
                    returnAmount = TokenContract.functions.returnAmount().call()
                    purpose = TokenContract.functions.purpose().call()
                    image_url_small = TokenContract.functions.getImageURL(0).call()
                    image_url_medium = TokenContract.functions.getImageURL(1).call()
                    image_url_large = TokenContract.functions.getImageURL(2).call()
                    owner_address = TokenContract.functions.owner().call()

                    # 企業リストから、企業名を取得する
                    company_name = ''
                    for company in company_list:
                        if to_checksum_address(company['address']) == owner_address:
                            company_name = company['corporate_name']

                    # 第三者認定（Sign）のイベント情報を検索する
                    event_filter = TokenContract.eventFilter(
                        'Sign', {
                            'filter':{},
                            'fromBlock':'earliest'
                        }
                    )
                    try:
                        entries = event_filter.get_all_entries()
                    except:
                        entries = []

                    certification = []
                    for entry in entries:
                        isSigned = False
                        if TokenContract.functions.\
                            signatures(to_checksum_address(entry['args']['signer'])).call() == 2:
                            isSigned = True

                        certification.append({
                            'signer':entry['args']['signer'],
                            'is_signed':isSigned
                        })

                    position_list.append({
                        'token': {
                            'token_address': mytoken['token_address'],
                            'token_template': token_template[1],
                            'company_name': company_name,
                            'name':name,
                            'symbol':symbol,
                            'totalSupply':totalSupply,
                            'faceValue':faceValue,
                            'interestRate':interestRate,
                            'interestPaymentDate1':interestPaymentDate1,
                            'interestPaymentDate2':interestPaymentDate2,
                            'redemptionDate':redemptionDate,
                            'redemptionAmount':redemptionAmount,
                            'returnDate':returnDate,
                            'returnAmount':returnAmount,
                            'purpose':purpose,
                            'image_url': [
                                {'type': 'small', 'url': image_url_small},
                                {'type': 'medium', 'url': image_url_medium},
                                {'type': "large", 'url': image_url_large}
                            ],
                            'certification':certification
                        },
                        'balance': balance,
                        'commitment': commitment
                    })

        self.on_success(res, position_list)

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
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        for account_address in request_json['account_address_list']:
            if not Web3.isAddress(account_address):
                raise InvalidParameterError

        return request_json
