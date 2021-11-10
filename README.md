# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-21.12-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

<img width="33%" align="right" src="https://user-images.githubusercontent.com/963333/71627030-97cd7480-2c33-11ea-9d3a-f77f424d954d.png"/>

## Features
- ibe-Wallet-API is RPC services that provides utility functions for building a wallet system on [ibet-Network](https://github.com/BoostryJP/ibet-Network).
- ibet-Wallet-API runs on token contracts and DEX contracts developed in the [ibet-SmartContract project](https://github.com/BoostryJP/ibet-SmartContract).

## Dependencies
- [python3](https://www.python.org/)
  - Version 3.8 or greater
- RDB
  - [PostgreSQL](https://www.postgresql.org/) - Version 10
  - [MySQL](https://www.mysql.com/) - Version 5.7
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - We support the official GoQuorum node of [ibet-Network](https://github.com/BoostryJP/ibet-Network).
  - We use [ganache-cli](https://github.com/trufflesuite/ganache-cli) for local development and unit testing, and we use the latest version.

## Supported contract version

* ibet-SmartContract: version 21.12.0


## Starting and Stopping the Server
Install packages
```
$ pip install -r requirements.txt
```

You can start (or stop) the API server with:
```
$ ./bin/run_server.sh start(stop)
```

## Running the tests
Install packages
```
$ pip install -r tests/requirements.txt
```

You can run the tests with:
```
$ pytest tests/
```

## Branching model

<p align='center'>
  <img alt="ibet" src="https://user-images.githubusercontent.com/963333/128963415-df122a46-b813-4832-a64e-7830a175f825.png"/>
</p>


## License

ibet-Wallet-API is licensed under the Apache License, Version 2.0.


## Contact information

We are committed to open-sourcing our work to support your use cases. 
We want to know how you use this library and what problems it helps you to solve. 
We have two communication channels for you to contact us:

* A [public discussion group](https://github.com/BoostryJP/ibet-Wallet-API/discussions)
where we will also share our preliminary roadmap, updates, events, and more.

* A private email alias at
[dev@boostry.co.jp](mailto:dev@boostry.co.jp)
where you can reach out to us directly about your use cases and what more we can
do to help and improve the library.
  
Please refrain from sending any sensitive or confidential information. 
If you wish to delete a message you've previously sent, please contact us.


## Sponsors

[BOOSTRY Co., Ltd.](https://boostry.co.jp/)
