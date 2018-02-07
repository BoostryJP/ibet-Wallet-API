var keythereum = require("keythereum");
var datadir = "/home/yoshihitoaso/eth_test_net";
var address= "0x1e770b6e52ddbee99209db0ef73fe7c18a119ed0";
const password = "password";

var keyObject = keythereum.importFromFile(address, datadir);
var privateKey = keythereum.recover(password, keyObject);
console.log(privateKey.toString('hex'));

