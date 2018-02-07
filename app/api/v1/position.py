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

LOG = log.get_logger()

# ------------------------------
# 保有トークン一覧
# ------------------------------
class MyTokens(BaseResource):
    '''
    Handle for endpoint: /v1/MyTokens/{eth_address}
    '''
    def on_get(self, req, res, eth_address):
        LOG.info('v1.Position.MyTokens')
        session = req.context['session']

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
            raise DataNotExistsError()

        for mytoken in portfolio_list:
            try:
                token_template_id = session.query(Contract).filter(
                    Contract.contract_address == mytoken['token_address']
                ).one().to_dict()['template_id']
                token_template = TokenTemplate.find_one(
                    session, token_template_id
                ).to_dict()
            except NoResultFound:
                raise DataNotExistsError()

            web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
            abi = json.loads(
                token_template['abi']\
                .replace("'", '"')\
                .replace('True', 'true')\
                .replace('False', 'false')
            )
            token_contract = web3.eth.contract(
                address=mytoken['token_address'],
                abi = abi,
                bytecode = token_template['bytecode'],
                bytecode_runtime = token_template['bytecode_runtime']
            )
            print(token_contract)

            owner = to_checksum_address(mytoken['account'])
            balance = token_contract.functions\
                .getBalanceOf(owner)\
                .call({"to":mytoken['token_address']})
            print(balance)
