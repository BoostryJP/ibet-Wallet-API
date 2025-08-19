/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  networks: {
    hardhat: {
      type: "http",
      url: "http://localhost:8545",
      chainId: 2017,
      gasPrice: 0,
      blockGasLimit: 800000000,
      hardfork: "berlin",
      throwOnTransactionFailures: false,
      throwOnCallFailures: false,
      allowBlocksWithSameTimestamp: true
    },
  },
  solidity: "0.8.23",
};
