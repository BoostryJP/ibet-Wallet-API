# -*- coding: utf-8 -*-

from web3 import Web3
from web3.middleware import geth_poa_middleware

from app import config
from app.contracts import Contract

web3 = Web3(Web3.HTTPProvider(config.WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)


class ContractModules():
    # 直近約定IDを取得
    def get_latest_agreementid(bond_exchange, order_id):
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', bond_exchange['address'])

        latest_agreementid = ExchangeContract.functions.latestAgreementId(order_id).call()
        return latest_agreementid

    # 直近約定amountを取得
    def get_latest_agreement_amount(bond_exchange, order_id):
        ExchangeContract = Contract.get_contract(
            'IbetStraightBondExchange', bond_exchange['address'])

        latest_agreement_amount = ExchangeContract.functions.latestAgreementId(order_id).call()
        return latest_agreement_amount
