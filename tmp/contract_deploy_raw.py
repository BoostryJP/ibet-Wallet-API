# -*- coding: utf-8 -*-
import json
import rlp

from ethereum.transactions import Transaction
import ethereum.utils as utils

from web3 import Web3

web3 = Web3(Web3.HTTPProvider('http://localhost:8545'))

from_address = '0x7ae52ca0c275982bb1c27e7ef5a6e920aad655c2'
from_privkey = '1ec98a827475a44e7727df8816a5717e99ad65b6880f7e299afd92cd88e2ec6c'

bytecode_str =  '6060604052341561000f57600080fd5b6107f48061001e6000396000f300606060405260043610610083576000357c0100000000000000000000000000000000000000000000000000000000900463ffffffff16806306fdde031461008857806318160ddd14610116578063313ce5671461013f57806370a082311461016e57806395d89b41146101bb578063a9059cbb14610249578063efe609c21461028b575b600080fd5b341561009357600080fd5b61009b610340565b6040518080602001828103825283818151815260200191508051906020019080838360005b838110156100db5780820151818401526020810190506100c0565b50505050905090810190601f1680156101085780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561012157600080fd5b6101296103de565b6040518082815260200191505060405180910390f35b341561014a57600080fd5b6101526103e4565b604051808260ff1660ff16815260200191505060405180910390f35b341561017957600080fd5b6101a5600480803573ffffffffffffffffffffffffffffffffffffffff169060200190919050506103f7565b6040518082815260200191505060405180910390f35b34156101c657600080fd5b6101ce61040f565b6040518080602001828103825283818151815260200191508051906020019080838360005b8381101561020e5780820151818401526020810190506101f3565b50505050905090810190601f16801561023b5780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561025457600080fd5b610289600480803573ffffffffffffffffffffffffffffffffffffffff169060200190919080359060200190919050506104ad565b005b341561029657600080fd5b61033e600480803590602001909190803590602001908201803590602001908080601f0160208091040260200160405190810160405280939291908181526020018383808284378201915050505050509190803590602001908201803590602001908080601f0160208091040260200160405190810160405280939291908181526020018383808284378201915050505050509190803560ff16906020019091905050610689565b005b60008054600181600116156101000203166002900480601f0160208091040260200160405190810160405280929190818152602001828054600181600116156101000203166002900480156103d65780601f106103ab576101008083540402835291602001916103d6565b820191906000526020600020905b8154815290600101906020018083116103b957829003601f168201915b505050505081565b60035481565b600260009054906101000a900460ff1681565b60046020528060005260406000206000915090505481565b60018054600181600116156101000203166002900480601f0160208091040260200160405190810160405280929190818152602001828054600181600116156101000203166002900480156104a55780601f1061047a576101008083540402835291602001916104a5565b820191906000526020600020905b81548152906001019060200180831161048857829003601f168201915b505050505081565b80600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205410156104f957600080fd5b600460008373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205481600460008573ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000205401101561058657600080fd5b80600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000206000828254039250508190555080600460008473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff168152602001908152602001600020600082825401925050819055508173ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff167fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef836040518082815260200191505060405180910390a35050565b83600460003373ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff1681526020019081526020016000208190555082600090805190602001906106e3929190610723565b5081600190805190602001906106fa929190610723565b5080600260006101000a81548160ff021916908360ff1602179055508360038190555050505050565b828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f1061076457805160ff1916838001178555610792565b82800160010185558215610792579182015b82811115610791578251825591602001919060010190610776565b5b50905061079f91906107a3565b5090565b6107c591905b808211156107c15760008160009055506001016107a9565b5090565b905600a165627a7a72305820bb445a805950f8247b98ae2f190e5bc6f6f4296cc64ed96d89f4b2d30ee9fec00029'

bytecode = utils.decode_hex(bytecode_str)

print(bytecode)

tx = Transaction(
    #nonce=web3.eth.getTransactionCount(from_address),
    nonce=31,
    to='',
    value=0,
    #gasprice=web3.eth.gasPrice,
    gasprice=18000000000,
    startgas=999999,
    data=bytecode,
    )

print('-----tx-----')
print(tx)

tx.sign(from_privkey)

raw_tx = rlp.encode(tx)
raw_tx_hex = web3.toHex(raw_tx)

print('-----rawTx-----')
print(raw_tx_hex)

#response = web3.eth.sendRawTransaction(raw_tx_hex)
#print(response)
