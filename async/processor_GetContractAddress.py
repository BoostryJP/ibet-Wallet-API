# -*- coding: utf-8 -*-
import time
from web3 import Web3
from config import engine, interval_time

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

while True:

    # コントラクトアドレスが登録されていないTokenの一覧を抽出
    contracts_unprocessed = engine.execute(
        "select * from contract where contract_address IS NULL"
    )

    for row in contracts_unprocessed:
        tx_hash = row['tx_hash']
        tx_hash_hex = '0x' + tx_hash[2:]
        tx_receipt = web3.eth.getTransactionReceipt(tx_hash_hex)
        if tx_receipt is not None :
            # ブロックの状態を確認して、コントラクトアドレスが登録されているかを確認する。
            if 'contractAddress' in tx_receipt.keys():
                admin_address = tx_receipt['from']
                contract_address = tx_receipt['contractAddress']

                # 登録済みトークン情報に発行者のアドレスと、コントラクトアドレスの登録を行う。
                query_contract = "update contract " + \
                    "set admin_address = \'" + admin_address + "\' , " + \
                    "contract_address = \'" + contract_address + "\' " + \
                    "where tx_hash = \'" + tx_hash + "\'"
                engine.execute(query_contract)

                # ウォレットのポートフォリオ情報を追加
                query_portfolio = "insert into portfolio " + \
                    "(account_address, contract_address)" + \
                    "values (\'" + admin_address + "\', \'" + contract_address + "\')"
                engine.execute(query_portfolio)

                print("issued --> " + contract_address)

    time.sleep(int(interval_time))
