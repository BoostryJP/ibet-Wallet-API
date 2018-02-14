# -*- coding: utf-8 -*-
import time
import json
from web3 import Web3
from config import engine, interval_time, WEB3_HTTP_PROVIDER

web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))

while True:

    event_issue = engine.execute(
        "select * from event_issue where status = 0"
    )

    for row in event_issue:
        tx_hash = row['tx_hash']
        tx_hash_hex = '0x' + tx_hash[2:]
        tx_receipt = web3.eth.getTransactionReceipt(tx_hash_hex)
        if tx_receipt is not None :
            if 'contractAddress' in tx_receipt.keys():
                contract_address = tx_receipt['contractAddress']
                template_id = row['template_id']
                token_template = engine.execute(
                    "select * from token_template where id = " + str(template_id)
                )
                for template in token_template:
                    abi_json = template['abi']
                    abi = json.loads(abi_json.replace("'", '"').replace('True', 'true').replace('False', 'false'))

                    bytecode = template['bytecode']
                    bytecode_runtime = template['bytecode_runtime']

                    print(contract_address)

                    token = web3.eth.contract(
                        address=contract_address,
                        abi = abi,
                        bytecode = bytecode,
                        bytecode_runtime = bytecode_runtime
                    )

                    event_filter = token.eventFilter(
                        'Issue', {
                            'filter': {},
                            'fromBlock':'earliest'
                        }
                    )

                    event = event_filter.get_all_entries()
                    print(event)
                    if len(event) >= 1:
                        print(event)
                        query = "update event_issue " + \
                            "set status = 1 where tx_hash = \'" + tx_hash + "\'"
                        engine.execute(query)
                        print("[Events] Issue --> " + contract_address)

    time.sleep(int(interval_time))
