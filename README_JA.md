# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-22.12-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

<a href='./README.md'>English</a> | 日本語

<img width="33%" align="right" src="https://user-images.githubusercontent.com/963333/71627030-97cd7480-2c33-11ea-9d3a-f77f424d954d.png"/>

## 機能概要

- ibet-Wallet-API は [ibet-Network](https://github.com/BoostryJP/ibet-Network) 上にウォレットシステムを構築するためのユーティリティ機能群を提供するRPCサービスです。
- ibet-Wallet-API は [ibet-SmartContract プロジェクト](https://github.com/BoostryJP/ibet-SmartContract) で開発されているトークンコントラクトや DEX コントラクトを利用して動作します。

## 依存
- [python3](https://www.python.org/)
  - バージョン 3.10
- RDB
  - [PostgreSQL](https://www.postgresql.org/) - バージョン 13
  - [MySQL](https://www.mysql.com/) - バージョン 5.7
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - [ibet-Network](https://github.com/BoostryJP/ibet-Network) の公式の GoQuorum をサポートしています。
  - 最新の [ganache](https://github.com/trufflesuite/ganache) (ganache-cli) をローカル開発およびユニットテストで利用しています。

## コントラクトのバージョン

* ibet-SmartContract: バージョン 22.12
* [詳細](./app/contracts/contract_version.md)を参照ください。

## セットアップ

### 事前準備

- Python実行環境を整備してください。
- PostgreSQLを設定し、以下のDBを事前に作成してください。
  - デフォルトでは以下の設定が必要になります。
    - ユーザー: ethuser
    - パスワード: ethpass
    - DB: ethcache
    - テスト用 DB: ethcache_test
- 以下のコントラクトを事前にデプロイする必要があります。
  - TokenList
  - PaymentGateway （任意）
  - IbetExchange （任意）
  - IbetEscrow （任意）
  - IbetSecurityTokenEscrow （任意）
  - E2EMessaging （任意）

### パッケージインストール

以下のコマンドで Python パッケージをインストールします。
```bash
$ pip install -r requirements.txt
```

### 環境変数の設定

設定可能な環境変数については以下のドキュメントを確認してください。

[List of Environment Variables](ENV_LIST.md)

### DB マイグレーション

[DB Migration Guide](migrations/README.md) を確認してください。


## 起動・停止

API サーバーの起動（停止）
```bash
$ ./bin/run_server.sh start(stop)
```

また、バッチプロセスは以下のように起動します。
```bash
$ ./bin/run_indexer.sh
$ ./bin/run_processor_notification.sh (*optional)
```

### API 仕様書

#### Swagger UI

サーバーを起動した状態で、[http://0.0.0.0:5000/docs](http://0.0.0.0:5000/docs) を開いてください。

Swagger UI 形式のドキュメントを参照することができるはずです。

![swagger](https://user-images.githubusercontent.com/963333/209300544-00afcea0-3deb-43a7-9b07-c77650459f5e.png)


#### ReDoc

同様に、[http://0.0.0.0:5000/redoc](http://0.0.0.0:5000/redoc) を開いてください。

ReDoc 形式のドキュメントを参照することができるはずです。

![redoc](https://user-images.githubusercontent.com/963333/209300694-2e8565e7-24ce-47ee-82a2-68d7cae92afb.png)


## テストの実行

テストで利用するパッケージをインストールします。
```bash
$ pip install -r tests/requirements.txt
```

以下のようにテストを実行します。
```bash
$ export UNIT_TEST_MODE=1
$ pytest tests/
```

## ブランチ作成方針

このリポジトリは以下の図で示されるフローでバージョン管理が行われています。

<p align='center'>
  <img alt="ibet_oss_branching_model" src="https://user-images.githubusercontent.com/963333/153906146-51104713-c93c-4c5d-8b0a-5cf59651ffff.png"/>
</p>


## ライセンス

ibet-Wallet-API は Apache License, Version 2.0 でライセンスされています。

## EoL の方針
メジャーバージョンはリリースから１年間サポートを行います。
例えば、v22.1 は v23.1 がリリースされるまでサポートされます。
サポート期間中は、致命的な問題（セキュリティ問題を含む）に対して、マイナーバージョンを発行して修正を行います（例：v22.1.1, v22.1.2 など）。

## 連絡先

私たちは、皆様のユースケースをサポートするために、オープンソースに取り組んでいます。
私たちは、あなたがこのライブラリをどのように使用し、どのような問題の解決に役立っているかを知りたいと思います。 
私たちは、2つのコミュニケーション用の手段を用意しています。

* [public discussion group](https://github.com/BoostryJP/ibet-Wallet-API/discussions) では、ロードマップ、アップデート、イベント等を共有します。

* [dev@boostry.co.jp](mailto:dev@boostry.co.jp) のEメール宛に連絡をいただければ、直接私たちに連絡することができます。

機密事項の送信はご遠慮ください。過去に送信したメッセージの削除を希望される場合は、ご連絡ください。

## スポンサー

[BOOSTRY Co., Ltd.](https://boostry.co.jp/)
