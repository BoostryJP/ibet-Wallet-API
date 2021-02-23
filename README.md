<p align='center'>
 <img alt="ibet" src="https://user-images.githubusercontent.com/963333/71627030-97cd7480-2c33-11ea-9d3a-f77f424d954d.png" width="300"/>
</p>
  
# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-1.2-blue.svg?cacheSeconds=2592000" />
  <a href="https:/doc.com" target="_blank">
    <img alt="Documentation" src="https://img.shields.io/badge/documentation-yes-brightgreen.svg" />
  </a>
  <a href="#" target="_blank">
    <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
  </a>
</p>

## About this repository

ibe-Wallet-API is an API service that provides various utilities to help you build Wallet services on [ibet network](https://github.com/BoostryJP/ibet-Network).

It supports the tokens developed by [ibet-SmartContract](https://github.com/BoostryJP/ibet-SmartContract).

## Supported contract version

* ibet-SmartContract: version 1.1.0

## Prerequisites

Set up an execution environment of Python 3.6 or higher.

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
$ pip install -r ./app/tests/requirements.txt
```

You can run the tests with:
```
$ pytest app/tests/
```

## License

ibet-Wallet-API is licensed under the Apache License, Version 2.0.

## Sponsors

[BOOSTRY Co., Ltd.](https://boostry.co.jp/)
