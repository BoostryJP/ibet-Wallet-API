# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-24.3-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

English | <a href='./README_JA.md'>日本語</a>

<img width="33%" align="right" src="https://user-images.githubusercontent.com/963333/71627030-97cd7480-2c33-11ea-9d3a-f77f424d954d.png"/>

## Features
- ibe-Wallet-API is RPC services that provides utility functions for building a wallet system on [ibet-Network](https://github.com/BoostryJP/ibet-Network).
- ibet-Wallet-API runs on token contracts and DEX contracts developed in the [ibet-SmartContract project](https://github.com/BoostryJP/ibet-SmartContract).

## Dependencies
- [python3](https://www.python.org/)
  - Version 3.11
- RDB
  - [PostgreSQL](https://www.postgresql.org/) - Version 15
  - [MySQL](https://www.mysql.com/) - Version 8.0
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - We support the official GoQuorum node of [ibet-Network](https://github.com/BoostryJP/ibet-Network).
  - We use [ganache](https://github.com/trufflesuite/ganache) (a.k.a. ganache-cli) for local development and unit testing, and we use the latest version.

## Supported contract version

* ibet-SmartContract: version 22.12
* See [details](./app/contracts/contract_version.md).

## Setup

### Prerequisites

- Need to set up a Python runtime environment.
- Need to create the DB on PostgreSQL beforehand.
  - By default, the following settings are required.
    - User: ethuser
    - Password: ethpass
    - DB: ethcache
    - DB for test use: ethcache_test
- Need to deploy the following contract beforehand.
  - TokenList
  - PaymentGateway (optional)
  - IbetExchange (optional)
  - IbetEscrow (optional)
  - IbetSecurityTokenEscrow (optional)
  - E2EMessaging (optional)

### Install packages

Install python packages with:
```bash
$ poetry install --no-root --only main -E ibet-explorer
```

### Setting environment variables

See the following documentation for environment variables that can be set in this system.

[List of Environment Variables](ENV_LIST.md)

### DB migrations

See [DB Migration Guide](migrations/README.md).


## Starting and Stopping the Server

You can start (or stop) the API server with:
```bash
$ ./bin/run_server.sh start(stop)
```

Open your browser at [http://0.0.0.0:5000](http://0.0.0.0:5000).

You will see the JSON response as:
```json
{"server":"ibet-Wallet-API"}
```

In addition, batch processes can be started with the following commands.

```bash
$ ./bin/run_indexer.sh
$ ./bin/run_processor.sh
```

### API docs

#### Swagger UI

Now go to [http://0.0.0.0:5000/docs](http://0.0.0.0:5000/docs).

You will see the automatic interactive API documentation provided by Swagger UI:

![swagger](https://user-images.githubusercontent.com/963333/209300544-00afcea0-3deb-43a7-9b07-c77650459f5e.png)

#### ReDoc

And now, go to [http://0.0.0.0:5000/redoc](http://0.0.0.0:5000/redoc).

You will see the alternative automatic documentation provided by ReDoc:

![redoc](https://user-images.githubusercontent.com/963333/209300694-2e8565e7-24ce-47ee-82a2-68d7cae92afb.png)


## Running the tests

Install packages with:
```bash
$ poetry install --no-root
```

You can run the tests with:
```bash
$ export UNIT_TEST_MODE=1
$ export RESPONSE_VALIDATION_MODE=1
$ pytest tests/
```

## Branching model

This repository is version controlled using the following flow.

<p align='center'>
  <img alt="ibet_oss_branching_model" src="https://user-images.githubusercontent.com/963333/153906146-51104713-c93c-4c5d-8b0a-5cf59651ffff.png"/>
</p>


## License

ibet-Wallet-API is licensed under the Apache License, Version 2.0.

## EoL policy
Each major version is supported for one year after release. 
For example, v22.1 is supported until v23.1 is released. 

It fixes critical problems, including critical security problems, 
in supported releases as needed by issuing minor revisions 
(for example, v22.1.1, v22.1.2, and so on).

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
