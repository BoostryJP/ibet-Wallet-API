# -*- coding: utf-8 -*-
from time import sleep
from web3 import Web3
from solc import compile_source

source_code = 'contract MyToken {     address issuer;     mapping (address => uint) balances;      event Issue(address account, uint amount);     event Transfer(address from, address to, uint amount);      function MyToken() {         issuer = msg.sender;     }      function issue(address account, uint amount) {         if (msg.sender != issuer) throw;         balances[account] += amount;     }      function transfer(address to, uint amount) {         if (balances[msg.sender] < amount) throw;          balances[msg.sender] -= amount;         balances[to] += amount;          Transfer(msg.sender, to, amount);     }      function getBalance(address account) constant returns (uint) {         return balances[account];     } }'

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
web3.personal.unlockAccount(web3.eth.accounts[0],"password",1000)

compile_sol = compile_source(source_code)

MyContract = web3.eth.contract(
    abi = compile_sol['<stdin>:MyToken']['abi'],
    bytecode = compile_sol['<stdin>:MyToken']['bin'],
    bytecode_runtime = compile_sol['<stdin>:MyToken']['bin-runtime'],
)

trans_hash = MyContract.deploy(transaction={'from':web3.eth.accounts[0]})
print(trans_hash)

# wait for mining
#trans_receipt = web3.eth.getTransactionReceipt(trans_hash)
#print(trans_receipt)

# get the contract address
#contract_address = trans_receipt['contractAddress']

# now we can instantiate the contract factory to get an instance of the contract.
#my_contract = MyContract(contract_address)
#print(my_contract)

# now you should be able to call the contract methods.
#balance = my_contract.call().getBalance(obj.eth.accounts[0])
#print(balance)
