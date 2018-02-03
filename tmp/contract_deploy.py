# -*- coding: utf-8 -*-
from web3 import Web3
from solc import compile_source

source_code = 'contract MyToken {  string public name;  string public symbol;  uint8 public decimals;  uint256 public totalSupply;  mapping (address => uint256) public balanceOf;  event Transfer(address indexed from, address indexed to, uint256 value);  event Issue(address indexed sender, uint256 value);  function MyToken(uint256 _supply, string _name, string _symbol, uint8 _decimals) public {    balanceOf[msg.sender] = _supply;    name = _name;    symbol = _symbol;    decimals = _decimals;    totalSupply = _supply;    Issue(msg.sender, _supply);  }  function transfer(address _to, uint256 _value) public {    require(balanceOf[msg.sender] > _value) ;    require(balanceOf[_to] + _value > balanceOf[_to]) ;    balanceOf[msg.sender] -= _value;    balanceOf[_to] += _value;    Transfer(msg.sender, _to, _value);  }  function getBalanceOf(address _owner) public constant returns (uint256){      return balanceOf[_owner];  }}'

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))
web3.personal.unlockAccount(web3.eth.accounts[0],"password",1000)

compile_sol = compile_source(source_code)

print('------abi------')
print(compile_sol['<stdin>:MyToken']['abi'])

print('------bin------')
print(compile_sol['<stdin>:MyToken']['bin'])

print('------bin-runtime------')
print(compile_sol['<stdin>:MyToken']['bin-runtime'])

MyContract = web3.eth.contract(
    abi = compile_sol['<stdin>:MyToken']['abi'],
    bytecode = compile_sol['<stdin>:MyToken']['bin'],
    bytecode_runtime = compile_sol['<stdin>:MyToken']['bin-runtime'],
)

#trans_hash = MyContract.deploy(transaction={'from':web3.eth.accounts[0]})
#print(trans_hash)
