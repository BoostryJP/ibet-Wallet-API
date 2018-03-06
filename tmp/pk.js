var keythereum = require("keythereum");
var datadir = "/home/yoshihito/eth_test_net";
var address= "0x590acc995c350dc21f92523b8937ce32f879e65a";
const password = "password";

var keyObject = keythereum.importFromFile(address, datadir);
var privateKey = keythereum.recover(password, keyObject);
console.log(privateKey.toString('hex'));

