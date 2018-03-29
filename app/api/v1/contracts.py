# -*- coding: utf-8 -*-
import json
import requests

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
# トークン一覧
# ------------------------------
class Contracts(BaseResource):
    '''
    Handle for endpoint: /v1/Contracts
    '''
    def on_get(self, req, res):
        LOG.info('v1.contracts.Contracts')
        session = req.context['session']

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        # TokenList-Contractへの接続
        list_contract_address = config.TOKEN_LIST_CONTRACT_ADDRESS
        list_contract_abi = json.loads(config.TOKEN_LIST_CONTRACT_ABI)

        ListContract = web3.eth.contract(
            address = to_checksum_address(list_contract_address),
            abi = list_contract_abi,
        )
        list_length = ListContract.functions.getListLength().call()

        # 企業リストの情報を取得する
        company_list = []
        try:
            company_list = requests.get(config.COMPANY_LIST_URL).json()
        except:
            pass

        token_list = []
        for i in range(list_length):
            # TokenList-Contractからトークンの情報を取得する
            token = ListContract.functions.getTokenByNum(i).call()
            token_address = token[0]
            token_template = token[1]
            owner_address = token[2]

            # IbetStraightBondフォーマットのもののみを選択する
            if token_template == 'IbetStraightBond':

                # トークンのABIを検索する
                abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template).first().abi
                token_abi = json.loads(abi_str)

                try:
                    # Token-Contractへの接続
                    TokenContract = web3.eth.contract(
                        address = to_checksum_address(token_address),
                        abi = token_abi
                    )

                    # Token-Contractから情報を取得する
                    name = TokenContract.functions.name().call()
                    symbol = TokenContract.functions.symbol().call()
                    totalSupply = TokenContract.functions.totalSupply().call()
                    faceValue = TokenContract.functions.faceValue().call()
                    interestRate = TokenContract.functions.interestRate().call()
                    interestPaymentDate1 = TokenContract.functions.interestPaymentDate1().call()
                    interestPaymentDate2 = TokenContract.functions.interestPaymentDate2().call()
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

                    token_list.append({
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
                    })
                except:
                    pass

        self.on_success(res, token_list)
