const fs = require("fs");
const solc = require("solc");
const Web3 = require("web3");
const Tx = require("ethereumjs-tx")

var privateKey = Buffer.from("67b41c23ccd8f0e948bf3bef584db23ef93796912cd6b04b2f7362a890162d89", "hex")

const web3 = new Web3(new Web3.providers.HttpProvider("http://localhost:8545"));

//const input = fs.readFileSync('MyToken.sol');
//const output = solc.compile(input.toString(), 1);
//const bytecode = output.contracts[':MyToken'].bytecode;
//const abi = JSON.parse(output.contracts[':MyToken'].interface);

//console.log(abi);
//console.log(bytecode);
//console.log(output.contracts[':MyToken'].interface);

// Compile the source code
const bytecode = "6060604052341561000f57600080fd5b6040516105813803806105818339810160405280805191906020018051820191906020018051820191906020018051600160a060020a0333166000908152600460205260408120879055909250905083805161006f9291602001906100de565b5060018280516100839291602001906100de565b506002805460ff191660ff8316179055600384905533600160a060020a03167fc65a3f767206d2fdcede0b094a4840e01c0dd0be1888b5ba800346eaa0123c168560405190815260200160405180910390a250505050610179565b828054600181600116156101000203166002900490600052602060002090601f016020900481019282601f1061011f57805160ff191683800117855561014c565b8280016001018555821561014c579182015b8281111561014c578251825591602001919060010190610131565b5061015892915061015c565b5090565b61017691905b808211156101585760008155600101610162565b90565b6103f9806101886000396000f3006060604052600436106100825763ffffffff7c010000000000000000000000000000000000000000000000000000000060003504166306fdde03811461008757806318160ddd14610111578063313ce5671461013657806370a082311461015f57806395d89b411461017e5780639b96eece14610191578063a9059cbb146101b0575b600080fd5b341561009257600080fd5b61009a6101d4565b60405160208082528190810183818151815260200191508051906020019080838360005b838110156100d65780820151838201526020016100be565b50505050905090810190601f1680156101035780820380516001836020036101000a031916815260200191505b509250505060405180910390f35b341561011c57600080fd5b610124610272565b60405190815260200160405180910390f35b341561014157600080fd5b610149610278565b60405160ff909116815260200160405180910390f35b341561016a57600080fd5b610124600160a060020a0360043516610281565b341561018957600080fd5b61009a610293565b341561019c57600080fd5b610124600160a060020a03600435166102fe565b34156101bb57600080fd5b6101d2600160a060020a0360043516602435610319565b005b60008054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561026a5780601f1061023f5761010080835404028352916020019161026a565b820191906000526020600020905b81548152906001019060200180831161024d57829003601f168201915b505050505081565b60035481565b60025460ff1681565b60046020526000908152604090205481565b60018054600181600116156101000203166002900480601f01602080910402602001604051908101604052809291908181526020018280546001816001161561010002031660029004801561026a5780601f1061023f5761010080835404028352916020019161026a565b600160a060020a031660009081526004602052604090205490565b600160a060020a03331660009081526004602052604090205481901161033e57600080fd5b600160a060020a0382166000908152600460205260409020548181011161036457600080fd5b600160a060020a033381166000818152600460205260408082208054869003905592851680825290839020805485019055917fddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef9084905190815260200160405180910390a350505600a165627a7a72305820d4877b1a3d489822384066f8d0e51bd355105982aa469d9d9bb4aaf64c88bcb50029";

const abi = JSON.parse('[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"","type":"address"}],"name":"balanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"getBalanceOf","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"inputs":[{"name":"_supply","type":"uint256"},{"name":"_name","type":"string"},{"name":"_symbol","type":"string"},{"name":"_decimals","type":"uint8"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"sender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Issue","type":"event"}]');

// Contract object
const contract = new web3.eth.contract(abi);

const supply = 10000;
const name = "testcoin";
const symbol = "TC";
const decimals = 1;

// Get contract data
//const contractData = contract.deploy({
//  data: "0x" + bytecode,
//  arguments: [supply, name, symbol, decimals]
//}).encodeABI();

const contractData = contract.new.getData.call(null,
  supply,
  name,
  symbol,
  decimals,
  {data: "0x" + bytecode}
)

const gasPrice = 20000000000;
const gasPriceHex = web3.toHex(gasPrice);
const gasLimitHex = web3.toHex(5000000);

const nonce = 4;
const nonceHex = web3.toHex(nonce);

const rawTx = {
    nonce: nonceHex,
    gasPrice: gasPriceHex,
    gasLimit: gasLimitHex,
    data: contractData,
    from: "0x1e770b6e52ddbee99209db0ef73fe7c18a119ed0",
    chainId: 4
};

const tx = new Tx(rawTx);
tx.sign(privateKey);
const serializedTx = tx.serialize();

console.log("0x" + serializedTx.toString("hex"));

web3.eth.sendRawTransaction('0x' + serializedTx.toString('hex'), (err, hash) => {
    if (err) { console.log(err); return; }

    // Log the tx, you can explore status manually with eth.getTransaction()
    console.log('contract creation tx: ' + hash);

    // Wait for the transaction to be mined
    waitForTransactionReceipt(hash);
});

//web3.eth.signTransaction(rawTx).then(console.log);

function waitForTransactionReceipt(hash) {
    console.log('waiting for contract to be mined');
    const receipt = web3.eth.getTransactionReceipt(hash);
    // If no receipt, try again in 1s
    if (receipt == null) {
        setTimeout(() => {
            waitForTransactionReceipt(hash);
        }, 1000);
    } else {
        // The transaction was mined, we can retrieve the contract address
        console.log('contract address: ' + receipt.contractAddress);
        //testContract(receipt.contractAddress);
    }
}
