# -*- coding: utf-8 -*-
import json

from web3 import Web3

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

trans_hash = '0x720b8ced479ef364ee1630b9286993f5326a11e269d4f789620d0ba44a60e434'
trans_receipt = web3.eth.getTransactionReceipt(trans_hash)
print('-----trans_hash-----')
print(trans_receipt)

contract_address = trans_receipt['contractAddress']

abi_json = "[{'constant': False, 'inputs': [{'name': 'account', 'type': 'address'}, {'name': 'amount', 'type': 'uint256'}], 'name': 'issue', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': False, 'inputs': [{'name': 'to', 'type': 'address'}, {'name': 'amount', 'type': 'uint256'}], 'name': 'transfer', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'constant': True, 'inputs': [{'name': 'account', 'type': 'address'}], 'name': 'getBalance', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'inputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'constructor'}, {'anonymous': False, 'inputs': [{'indexed': False, 'name': 'account', 'type': 'address'}, {'indexed': False, 'name': 'amount', 'type': 'uint256'}], 'name': 'Issue', 'type': 'event'}, {'anonymous': False, 'inputs': [{'indexed': False, 'name': 'from', 'type': 'address'}, {'indexed': False, 'name': 'to', 'type': 'address'}, {'indexed': False, 'name': 'amount', 'type': 'uint256'}], 'name': 'Transfer', 'type': 'event'}]"

abi = json.loads(abi_json.replace("'", '"').replace('True', 'true').replace('False', 'false'))

bytecode = "6060604052341561000f57600080fd5b336000806101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506103d78061005e6000396000f300606060405260043610610057576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff168063867904b41461005c578063a9059cbb1461009e578063f8b2cb4f146100e0575b600080fd5b341561006757600080fd5b61009c600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803590602001909190505061012d565b005b34156100a957600080fd5b6100de600480803573ffffffffffffffffffffffffffffffffffffffff169060200190919080359060200190919050506101d9565b005b34156100eb57600080fd5b610117600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091905050610362565b6040518082815260200191505060405180910390f35b6000809054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614151561018857600080fd5b80600160008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055505050565b80600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054101561022557600080fd5b80600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600160008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055507fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef338383604051808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020018373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001828152602001935050505060405180910390a15050565b6000600160008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205490509190505600a165627a7a72305820ea5065c9497af6263d046d6e06e3c036a504796f1ccb406510b9b8e980715cba0029"

bytecode_runtime = "606060405260043610610057576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff168063867904b41461005c578063a9059cbb1461009e578063f8b2cb4f146100e0575b600080fd5b341561006757600080fd5b61009c600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803590602001909190505061012d565b005b34156100a957600080fd5b6100de600480803573ffffffffffffffffffffffffffffffffffffffff169060200190919080359060200190919050506101d9565b005b34156100eb57600080fd5b610117600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091905050610362565b6040518082815260200191505060405180910390f35b6000809054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff1614151561018857600080fd5b80600160008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055505050565b80600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16815260200190815260200160002054101561022557600080fd5b80600160003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600160008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055507fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef338383604051808473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020018373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001828152602001935050505060405180910390a15050565b6000600160008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205490509190505600a165627a7a72305820ea5065c9497af6263d046d6e06e3c036a504796f1ccb406510b9b8e980715cba0029"

MyContract = web3.eth.contract(
    abi = abi,
    bytecode = bytecode,
    bytecode_runtime = bytecode_runtime,
)

my_contract = MyContract(contract_address)

balance = my_contract.call().getBalance('0x7ae52ca0c275982bb1c27e7ef5a6e920aad655c2')
print('-----balance-----')
print(balance)
