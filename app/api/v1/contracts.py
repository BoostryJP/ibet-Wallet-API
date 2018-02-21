# -*- coding: utf-8 -*-
import json

from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import Contract, TokenTemplate
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

        list_contract_address = '0x4E017fbE3d2F876335478Ee7a4CeFd3EEDf8fdbA'
        list_contract_abi = json.loads('[{"constant": false,"inputs": [{"name": "_token_address","type": "address"},{"name": "_token_template","type": "string"}],"name": "register","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": true,"inputs": [{"name": "_num","type": "uint256"}],"name": "getTokenByNum","outputs": [{"name": "token_address","type": "address"},{"name": "token_template","type": "string"},{"name": "owner_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "_token_address","type": "address"}],"name": "getOwnerAddress","outputs": [{"name": "issuer_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "_token_address","type": "address"}],"name": "getTokenByAddress","outputs": [{"name": "token_address","type": "address"},{"name": "token_template","type": "string"},{"name": "owner_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [],"name": "getListLength","outputs": [{"name": "length","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": false,"inputs": [{"name": "_token_address","type": "address"},{"name": "_new_owner_address","type": "address"}],"name": "changeOwner","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"}]')

        ListContract = web3.eth.contract(
            address = list_contract_address,
            abi = list_contract_abi,
        )

        list_length = ListContract.functions.getListLength().call()

        token_list = []
        for i in range(list_length):
            token = ListContract.functions.getTokenByNum(i).call()
            token_address = token[0]
            token_template = token[1]
            abi_str = session.query(TokenTemplate).filter(TokenTemplate.template_name == token_template).first().abi
            token_abi = json.loads(abi_str)

            TokenContract = web3.eth.contract(
                address = token_address,
                abi = token_abi
            )

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

            token_list.append({
                'token_address':token_address,
                'token_template':token_template,
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
            })

        self.on_success(res, token_list)
