# -*- coding: utf-8 -*-
import json
from sqlalchemy.orm.exc import NoResultFound
from cerberus import Validator, ValidationError

from web3 import Web3
from eth_utils import to_checksum_address

from app import log
from app.api.common import BaseResource
from app.model import TokenTemplate, Contract, Portfolio
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
        address_list = request_json['address_list']

        web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))

        list_contract_address = '0x4E017fbE3d2F876335478Ee7a4CeFd3EEDf8fdbA'
        list_contract_abi = json.loads('[{"constant": false,"inputs": [{"name": "_token_address","type": "address"},{"name": "_token_template","type": "string"}],"name": "register","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"},{"constant": true,"inputs": [{"name": "_num","type": "uint256"}],"name": "getTokenByNum","outputs": [{"name": "token_address","type": "address"},{"name": "token_template","type": "string"},{"name": "owner_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "_token_address","type": "address"}],"name": "getOwnerAddress","outputs": [{"name": "issuer_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [{"name": "_token_address","type": "address"}],"name": "getTokenByAddress","outputs": [{"name": "token_address","type": "address"},{"name": "token_template","type": "string"},{"name": "owner_address","type": "address"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": true,"inputs": [],"name": "getListLength","outputs": [{"name": "length","type": "uint256"}],"payable": false,"stateMutability": "view","type": "function"},{"constant": false,"inputs": [{"name": "_token_address","type": "address"},{"name": "_new_owner_address","type": "address"}],"name": "changeOwner","outputs": [],"payable": false,"stateMutability": "nonpayable","type": "function"}]')

        ListContract = web3.eth.contract(
            address = list_contract_address,
            abi = list_contract_abi,
        )

        position_list = []
        for eth_address in address_list:
            # ポートフォリオのリストを取得
            portfolio_list = []
            try:
                portfolio_db_list = session.query(Portfolio).filter(
                    Portfolio.account_address == eth_address
                ).all()
                for portfolio_db in portfolio_db_list:
                    row = portfolio_db.to_dict()
                    portfolio_list.append({
                        "account":row['account_address'],
                        "token_address":row['contract_address']
                    })
            except NoResultFound:
                continue

            token_template = None
            for mytoken in portfolio_list:
                token_address = to_checksum_address(mytoken['token_address'])
                token_template = ListContract.functions.getTokenByAddress(token_address).call()
                print(token_template)
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

                position_list.append({
                    'token_address': mytoken['token_address'],
                    'balance': balance,
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

        self.on_success(res, position_list)

    @staticmethod
    def validate(req):
        request_json = req.context['data']
        if request_json is None:
            raise InvalidParameterError

        validator = Validator({
            'address_list': {
                'type': 'list',
                'schema': {'type': 'string'},
                'empty': False,
                'required': True
            }
        })

        if not validator.validate(request_json):
            raise InvalidParameterError(validator.errors)

        return request_json
