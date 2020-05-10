# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

from locust import HttpLocust, TaskSet, task

import os
import json
from app import config 
from web3.auto import w3
from eth_utils import decode_hex, to_checksum_address

# テスト用のアカウント
private_key = "0000000000000000000000000000000000000000000000000000000000000001"
eth_address = "0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf"

# コントラクト情報
contracts = json.load(open('../../../data/contracts.json' , 'r'))
personalinfo_contract_address = \
	to_checksum_address(config.PERSONAL_INFO_CONTRACT_ADDRESS)
personalinfo_contract_abi = contracts['PersonalInfo']['abi']

# Basic認証
basic_auth_user = config.BASIC_AUTH_USER
basic_auth_pass = config.BASIC_AUTH_PASS

class LoadTestTaskSet(TaskSet):
	def on_start(self):
		self.client.get(
			"/",
			auth = (basic_auth_user, basic_auth_pass),
			verify=False
		)

	@staticmethod
	def get_tx_info(self, eth_address):
		response = self.client.get(
			"/v2/Eth/TransactionCount/" + eth_address,
			auth = (basic_auth_user, basic_auth_pass),
			verify=False
		)
		response_json = json.loads(
			response.content.decode('utf8').replace("'", '"'))

		nonce = response_json["data"]["nonce"]
		gas_price = response_json["data"]["gasprice"]

		return nonce, gas_price

	@task
	def eth_sendrawtransaction(self):
		contract = w3.eth.contract(
			address = personalinfo_contract_address,
			abi = personalinfo_contract_abi,
		)

		nonce, gas_price = LoadTestTaskSet.get_tx_info(self, eth_address)

		txn = contract.functions.register(eth_address, '').buildTransaction({
			'chainId': 2017,
			'gas': 4000000,
			'gasPrice': gas_price,
			'nonce': nonce,
		})

		signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)

		raw_tx_hex_list = []
		raw_tx_hex_list.append(str(signed_txn.rawTransaction.hex()))

		payload = {'raw_tx_hex_list': raw_tx_hex_list}
		headers = {'content-type': 'application/json'}
		response = self.client.post(
			"/v2/Eth/SendRawTransaction",
			headers = headers,
			auth = (basic_auth_user, basic_auth_pass),
			data = json.dumps(payload),
			verify=False
		)
		print(response.content)

class Website(HttpLocust):
	task_set = LoadTestTaskSet

	# task実行の最短待ち時間
	min_wait = 1000
	# task実行の最大待ち時間
	max_wait = 1000
