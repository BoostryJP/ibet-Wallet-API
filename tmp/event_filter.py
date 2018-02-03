# -*- coding: utf-8 -*-
import json

from web3 import Web3

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

trans_hash = '0x873d4fd3d8e9b02beaab7f54342a57ce5abe3c100a50d830dc8994f3a3bfc2dc'
trans_receipt = web3.eth.getTransactionReceipt(trans_hash)

contract_address = trans_receipt['contractAddress']
print(contract_address)

abi_json = "[{'constant': True, 'inputs': [], 'name': 'name', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'totalSupply', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'decimals', 'outputs': [{'name': '', 'type': 'uint8'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '', 'type': 'address'}], 'name': 'balanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [], 'name': 'symbol', 'outputs': [{'name': '', 'type': 'string'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': True, 'inputs': [{'name': '_owner', 'type': 'address'}], 'name': 'getBalanceOf', 'outputs': [{'name': '', 'type': 'uint256'}], 'payable': False, 'stateMutability': 'view', 'type': 'function'}, {'constant': False, 'inputs': [{'name': '_to', 'type': 'address'}, {'name': '_value', 'type': 'uint256'}], 'name': 'transfer', 'outputs': [], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'function'}, {'inputs': [{'name': '_supply', 'type': 'uint256'}, {'name': '_name', 'type': 'string'}, {'name': '_symbol', 'type': 'string'}, {'name': '_decimals', 'type': 'uint8'}], 'payable': False, 'stateMutability': 'nonpayable', 'type': 'constructor'}, {'anonymous': False, 'inputs': [{'indexed': True, 'name': 'from', 'type': 'address'}, {'indexed': True, 'name': 'to', 'type': 'address'}, {'indexed': False, 'name': 'value', 'type': 'uint256'}], 'name': 'Transfer', 'type': 'event'}, {'anonymous': False, 'inputs': [{'indexed': True, 'name': 'sender', 'type': 'address'}, {'indexed': False, 'name': 'value', 'type': 'uint256'}], 'name': 'Issue', 'type': 'event'}]"

abi = json.loads(abi_json.replace("'", '"').replace('True', 'true').replace('False', 'false'))

bytecode = "6060604052341561000f57600080fd5b6040516108803803806108808339810160405280805190602001909190805182019190602001805182019190602001805190602001909190505083600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000208190555082600090805190602001906100a3929190610134565b5081600190805190602001906100ba929190610134565b5080600260006101000a81548160ff021916908360ff160217905550836003819055503373ffffffffffffffffffffffffffffffffffffffff167fc65a3f767206d2fdcede0b094a4840e01c0dd0be1888b5ba800346eaa0123c16856040518082815260200191505060405180910390a2505050506101d9565b828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f1061017557805160ff19168380011785556101a3565b828001600101855582156101a3579182015b828111156101a2578251825591602001919060010190610187565b5b5090506101b091906101b4565b5090565b6101d691905b808211156101d25760008160009055506001016101ba565b5090565b90565b610698806101e86000396000f300606060405260043610610083576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff16806306fdde031461008857806318160ddd14610116578063313ce5671461013f57806370a082311461016e57806395d89b41146101bb5780639b96eece14610249578063a9059cbb14610296575b600080fd5b341561009357600080fd5b61009b6102d8565b6040518080602001828103825283818151815260200191508051906020019080838360005b838110156100db5780820151818401526020810190506100c0565b50505050905090810190601f1680156101085780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561012157600080fd5b610129610376565b6040518082815260200191505060405180910390f35b341561014a57600080fd5b61015261037c565b604051808260ff1660ff16815260200191505060405180910390f35b341561017957600080fd5b6101a5600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190505061038f565b6040518082815260200191505060405180910390f35b34156101c657600080fd5b6101ce6103a7565b6040518080602001828103825283818151815260200191508051906020019080838360005b8381101561020e5780820151818401526020810190506101f3565b50505050905090810190601f16801561023b5780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561025457600080fd5b610280600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091905050610445565b6040518082815260200191505060405180910390f35b34156102a157600080fd5b6102d6600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803590602001909190505061048e565b005b60008054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561036e5780601f106103435761010080835404028352916020019161036e565b820191906000526020600020905b81548152906001019060200180831161035157829003601f168201915b505050505081565b60035481565b600260009054906101000a900460ff1681565b60046020528060005260406000206000915090505481565b60018054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561043d5780601f106104125761010080835404028352916020019161043d565b820191906000526020600020905b81548152906001019060200180831161042057829003601f168201915b505050505081565b6000600460008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020549050919050565b80600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020541115156104db57600080fd5b600460008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205481600460008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020540111151561056957600080fd5b80600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600460008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055508173ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef836040518082815260200191505060405180910390a350505600a165627a7a723058207ba76340c66960e8bce6d6fe82e5e41d5fbe3d45b52d63a3f46cba33812639060029"

bytecode_runtime = "606060405260043610610083576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff16806306fdde031461008857806318160ddd14610116578063313ce5671461013f57806370a082311461016e57806395d89b41146101bb5780639b96eece14610249578063a9059cbb14610296575b600080fd5b341561009357600080fd5b61009b6102d8565b6040518080602001828103825283818151815260200191508051906020019080838360005b838110156100db5780820151818401526020810190506100c0565b50505050905090810190601f1680156101085780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561012157600080fd5b610129610376565b6040518082815260200191505060405180910390f35b341561014a57600080fd5b61015261037c565b604051808260ff1660ff16815260200191505060405180910390f35b341561017957600080fd5b6101a5600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190505061038f565b6040518082815260200191505060405180910390f35b34156101c657600080fd5b6101ce6103a7565b6040518080602001828103825283818151815260200191508051906020019080838360005b8381101561020e5780820151818401526020810190506101f3565b50505050905090810190601f16801561023b5780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561025457600080fd5b610280600480803573ffffffffffffffffffffffffffffffffffffffff16906020019091905050610445565b6040518082815260200191505060405180910390f35b34156102a157600080fd5b6102d6600480803573ffffffffffffffffffffffffffffffffffffffff1690602001909190803590602001909190505061048e565b005b60008054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561036e5780601f106103435761010080835404028352916020019161036e565b820191906000526020600020905b81548152906001019060200180831161035157829003601f168201915b505050505081565b60035481565b600260009054906101000a900460ff1681565b60046020528060005260406000206000915090505481565b60018054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561043d5780601f106104125761010080835404028352916020019161043d565b820191906000526020600020905b81548152906001019060200180831161042057829003601f168201915b505050505081565b6000600460008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020549050919050565b80600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020541115156104db57600080fd5b600460008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205481600460008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020540111151561056957600080fd5b80600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600460008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055508173ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef836040518082815260200191505060405180910390a350505600a165627a7a723058207ba76340c66960e8bce6d6fe82e5e41d5fbe3d45b52d63a3f46cba33812639060029"

my_contract = web3.eth.contract(
    address=contract_address,
    abi = abi,
    bytecode = bytecode,
    bytecode_runtime = bytecode_runtime
)

transfer_filter = my_contract.eventFilter('Transfer', {'filter': {},'fromBlock':'earliest'})
print(transfer_filter.get_new_entries())
#[]

print(transfer_filter.get_all_entries())
#[{'args': {'from': '0x7AE52CA0c275982bB1c27e7eF5a6e920aAd655C2', 'to': '0x9bA95eC04393f718628F07b0cA01377Cb6D01e73', 'value': 100}, 'event': 'Transfer', 'logIndex': 0, 'transactionIndex': 0, 'transactionHash': HexBytes('0x274fbe27f2969b7d2932c71093c1caf2c0f598e4a36cc7ed691dff683ad90bf9'), 'address': '0x89a24897486eCeF71A6752450D100E85f886E222', 'blockHash': HexBytes('0x3035eb62421f84cc0c4e4bc355fbb89b2d4db848282ed2d73a3f1a51d07c67ea'), 'blockNumber': 964}, {'args': {'from': '0x7AE52CA0c275982bB1c27e7eF5a6e920aAd655C2', 'to': '0x9bA95eC04393f718628F07b0cA01377Cb6D01e73', 'value': 100}, 'event': 'Transfer', 'logIndex': 0, 'transactionIndex': 0, 'transactionHash': HexBytes('0x3bd1b93f50e6d304b9cd29ca1f9e23405f516a718364c7fee559a2c879c49ff9'), 'address': '0x89a24897486eCeF71A6752450D100E85f886E222', 'blockHash': HexBytes('0xedfba8412f852752ecd253659e7b3fd6694b61fe69115a887774724b78664a46'), 'blockNumber': 986}]

transfer_filter = my_contract.eventFilter('Transfer', {'filter': {},'fromBlock':965})
print(transfer_filter.get_all_entries())
#[{'args': {'from': '0x7AE52CA0c275982bB1c27e7eF5a6e920aAd655C2', 'to': '0x9bA95eC04393f718628F07b0cA01377Cb6D01e73', 'value': 100}, 'event': 'Transfer', 'logIndex': 0, 'transactionIndex': 0, 'transactionHash': HexBytes('0x3bd1b93f50e6d304b9cd29ca1f9e23405f516a718364c7fee559a2c879c49ff9'), 'address': '0x89a24897486eCeF71A6752450D100E85f886E222', 'blockHash': HexBytes('0xedfba8412f852752ecd253659e7b3fd6694b61fe69115a887774724b78664a46'), 'blockNumber': 986}]
