# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-21.7-blue.svg?cacheSeconds=2592000" />
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

## Dependencies

- [python3](https://www.python.org/downloads/release/python-3811/) version 3.8 or greater


## Supported contract version

* ibet-SmartContract: version 21.6.0


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
