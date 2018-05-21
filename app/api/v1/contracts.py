# -*- coding: utf-8 -*-
import os
import json
import requests

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.errors import AppError, InvalidParameterError, DataNotExistsError
from app import config

LOG = log.get_logger()

# ------------------------------
# トークン一覧
# ------------------------------
class Contracts(BaseResource):
    def __init__(self):
        super().__init__()
        self.web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
        if config.WEB3_CHAINID == '4' or '2017':
            from web3.middleware import geth_poa_middleware
            self.web3.middleware_stack.inject(geth_poa_middleware, layer=0)

    '''
    Handle for endpoint: /v1/Contracts
    '''
    def on_get(self, req, res):
        LOG.info('v1.contracts.Contracts')

        # Validation
        request_json = Contracts.validate(req)

        # TokenList-Contractへの接続
        list_contract_address = os.environ.get('TOKEN_LIST_CONTRACT_ADDRESS')
        list_contract_abi = json.loads(config.TOKEN_LIST_CONTRACT_ABI)

        ListContract = self.web3.eth.contract(
            address = to_checksum_address(list_contract_address),
            abi = list_contract_abi,
        )
        list_length = ListContract.functions.getListLength().call()

        if request_json['cursor'] != None and request_json['cursor'] > list_length:
            raise InvalidParameterError("cursor parameter must be less than token list num")

        # パラメータを設定
        cursor = request_json['cursor']
        if cursor is None:
            cursor = list_length
        limit = request_json['limit']
        if limit is None:
            limit = 10

        # 企業リストの情報を取得する
        company_list = []
        try:
            if config.APP_ENV == 'local':
                company_list = json.load(open('data/company_list.json' , 'r'))
            else:
                company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            pass

        token_list = []
        # TokenListを降順に調べる(登録が新しい順)
        for i in reversed(range(0, cursor)):
            if len(token_list) >= limit:
                break

            # TokenList-Contractからトークンの情報を取得する
            token = ListContract.functions.getTokenByNum(i).call()

            token_detail = self.get_token_detail(token_id = i,
                                                 company_list = company_list,
                                                 token_address = token[0],
                                                 token_template = token[1],
                                                 owner_address = token[2])
            if token_detail != None:
                token_list.append(token_detail)

        self.on_success(res, token_list)


    def get_token_detail(self, token_id, token_address, token_template, owner_address, company_list):
        """
        トークン詳細を取得する。
        取得に失敗した場合はNoneを返す。
        """

        if token_template == 'IbetStraightBond':
            # トークンのABIを検索する
            abi_str = config.STRAIGHT_BOND_ABI['abi']
            token_abi = json.loads(abi_str)

            try:
                # Token-Contractへの接続
                TokenContract = self.web3.eth.contract(
                    address = to_checksum_address(token_address),
                    abi = token_abi
                )

                # 償還済みの銘柄はリストに返さない
                if TokenContract.functions.isRedeemed().call() == True:
                    return None

                # Token-Contractから情報を取得する
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
                image_url_s = TokenContract.functions.image_urls(0).call()
                image_url_m = TokenContract.functions.image_urls(1).call()
                image_url_l = TokenContract.functions.image_urls(2).call()

                # 企業リストから、企業名とRSA鍵を取得する
                company_name = ''
                rsa_publickey = ''
                for company in company_list:
                    if to_checksum_address(company['address']) == owner_address:
                        company_name = company['corporate_name']
                        rsa_publickey = company['rsa_publickey']

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

                return {
                    'id': token_id,
                    'token_address':token_address,
                    'token_template':token_template,
                    'owner_address': owner_address,
                    'company_name':company_name,
                    'rsa_publickey':rsa_publickey,
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
                    'image_url':[
                        {'type':'small', 'url':image_url_s},
                        {'type':'medium', 'url':image_url_m},
                        {'type':'large', 'url':image_url_l},
                    ],
                    'certification':certification
                }
            except Exception as e:
                return None

    @staticmethod
    def validate(req):
        request_json = {
            'cursor': req.get_param('cursor'),
            'limit': req.get_param('limit'),
        }

        validator = Validator({
            'cursor': {
                'type': 'integer',
                'coerce': int,
                'required': False,
                'nullable': True,
            },
            'limit': {
                'type': 'integer',
                'coerce': int,
                'required': False,
                'nullable': True,
            },
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return validator.document
