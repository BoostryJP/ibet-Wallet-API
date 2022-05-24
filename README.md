# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-22.6-blue.svg?cacheSeconds=2592000" />
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
  - [PostgreSQL](https://www.postgresql.org/) - Version 13
  - [MySQL](https://www.mysql.com/) - Version 5.7
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - We support the official GoQuorum node of [ibet-Network](https://github.com/BoostryJP/ibet-Network).
  - We use [ganache](https://github.com/trufflesuite/ganache) for local development and unit testing, and we use the latest version.

## Supported contract version

* ibet-SmartContract: version 22.3.0

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
$ pip install -r requirements.txt
```

### Setting environment variables

The main environment variables are as follows. 

<table style="border-collapse: collapse" id="env-table">
    <tr bgcolor="#000000">
        <th style="width: 25%">Variable Name</th>
        <th style="width: 10%">Required</th>
        <th style="width: 30%">Details</th>
        <th>Example</th>
    </tr>
    <tr>
        <td>APP_ENV</td>
        <td>False</td>
        <td nowrap>Running environment</td>
        <td>local (*default) / dev / live</td>
    </tr>
    <tr>
        <td>NETWORK</td>
        <td>False</td>
        <td nowrap>Running network</td>
        <td>IBET (*default) / IBETFIN</td>
    </tr>
    <tr>
        <td>WEB3_CHAINID</td>
        <td>False</td>
        <td nowrap>Blockchain network ID</td>
        <td>1010032</td>
    </tr>
    <tr>
        <td>COMPANY_LIST_URL</td>
        <td>True</td>
        <td nowrap>Company list URL</td>
        <td></td>
    </tr>
    <tr>
        <td>COMPANY_LIST_LOCAL_MODE</td>
        <td>False</td>
        <td nowrap>Using the local mode of the company list</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>DATABASE_URL</td>
        <td>False</td>
        <td nowrap>Database URL</td>
        <td>postgresql://ethuser:ethpass@localhost:5432/ethcache</td>
    </tr>
    <tr>
        <td>TEST_DATABASE_URL</td>
        <td>False</td>
        <td nowrap>Test database URL</td>
        <td>postgresql://ethuser:ethpass@localhost:5432/ethcache_test</td>
    </tr>
    <tr>
        <td>DATABASE_SCHEMA</td>
        <td>False</td>
        <td nowrap>Database schema</td>
        <td></td>
    </tr>
    <tr>
        <td>WEB3_HTTP_PROVIDER</td>
        <td>False</td>
        <td nowrap>Web3 provider</td>
        <td>http://localhost:8545</td>
    </tr>
    <tr>
        <td>BOND_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Using ibet Bond token</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>SHARE_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Using ibet Share token</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>MEMBERSHIP_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Using ibet Membership token</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>COUPON_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Using ibet Coupon token</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>AGENT_ADDRESS</td>
        <td>True</td>
        <td nowrap>Paying agent address (set only if you use IbetExchange)</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>TOKEN_LIST_CONTRACT_ADDRESS</td>
        <td>True</td>
        <td nowrap>TokenList contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>PERSONAL_INFO_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>PersonalInfo contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>PAYMENT_GATEWAY_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>PaymentGateway contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_SB_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>IbetExchange contract address for Bond tokens</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>IbetExchange contract address for Share tokens</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>IbetExchange contract address for Membership tokens</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_CP_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>IbetExchange contract address for Coupon tokens</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_ESCROW_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Ibet Escrow contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Ibet Security Token Escrow contract address</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
</table>

Other environment variables that can be set can be found in `app/config.py`.

### DB migrations

See [migrations/README.md](migrations/README.md).


## Starting and Stopping the Server

You can start (or stop) the API server with:
```bash
$ ./bin/run_server.sh start(stop)
```

In addition, batch processes can be started with the following commands.

```bash
$ ./bin/run_indexer.sh
$ ./bin/run_processor_notification.sh (*optional)
```

## Running the tests

Install packages with:
```bash
$ pip install -r tests/requirements.txt
```

You can run the tests with:
```bash
$ pytest tests/
```

## Branching model

<p align='center'>
  <img alt="ibet_oss_branching_model" src="https://user-images.githubusercontent.com/963333/153906146-51104713-c93c-4c5d-8b0a-5cf59651ffff.png"/>
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
