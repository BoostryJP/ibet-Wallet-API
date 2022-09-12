# ibet Wallet API

<p>
  <img alt="Version" src="https://img.shields.io/badge/version-22.9-blue.svg?cacheSeconds=2592000" />
  <img alt="License: Apache--2.0" src="https://img.shields.io/badge/License-Apache--2.0-yellow.svg" />
</p>

<a href='./README.md'>English</a> | 日本語

<img width="33%" align="right" src="https://user-images.githubusercontent.com/963333/71627030-97cd7480-2c33-11ea-9d3a-f77f424d954d.png"/>

## 機能概要

- ibet-Wallet-API は [ibet-Network](https://github.com/BoostryJP/ibet-Network) 上にウォレットシステムを構築するためのユーティリティ機能群を提供するRPCサービスです。
- ibet-Wallet-API は [ibet-SmartContract プロジェクト](https://github.com/BoostryJP/ibet-SmartContract) で開発されているトークンコントラクトや DEX コントラクトを利用して動作します。

## 依存
- [python3](https://www.python.org/)
  - バージョン 3.10 以上
- RDB
  - [PostgreSQL](https://www.postgresql.org/) - バージョン 13
  - [MySQL](https://www.mysql.com/) - バージョン 5.7
- [GoQuorum](https://github.com/ConsenSys/quorum)
  - [ibet-Network](https://github.com/BoostryJP/ibet-Network) の公式の GoQuorum をサポートしています。
  - 最新の [ganache](https://github.com/trufflesuite/ganache) (ganache-cli) をローカル開発およびユニットテストで利用しています。

## コントラクトのバージョン

* ibet-SmartContract: バージョン 22.6

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

主要な環境変数は以下の通りです。

<table style="border-collapse: collapse" id="env-table">
    <tr bgcolor="#000000">
        <th style="width: 25%">環境変数名</th>
        <th style="width: 10%">必須</th>
        <th style="width: 30%">詳細</th>
        <th>設定例</th>
    </tr>
    <tr>
        <td>APP_ENV</td>
        <td>False</td>
        <td nowrap>実行環境</td>
        <td>local (*default) / dev / live</td>
    </tr>
    <tr>
        <td>NETWORK</td>
        <td>False</td>
        <td nowrap>実行ネットワーク</td>
        <td>IBET (*default) / IBETFIN</td>
    </tr>
    <tr>
        <td>WEB3_CHAINID</td>
        <td>False</td>
        <td nowrap>ブロックチェーンネットワークID</td>
        <td>1010032</td>
    </tr>
    <tr>
        <td>COMPANY_LIST_URL</td>
        <td>True</td>
        <td nowrap>発行企業リストURL</td>
        <td></td>
    </tr>
    <tr>
        <td>COMPANY_LIST_LOCAL_MODE</td>
        <td>False</td>
        <td nowrap>発行企業リストローカルモード</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>DATABASE_URL</td>
        <td>False</td>
        <td nowrap>データベース URL</td>
        <td>postgresql://ethuser:ethpass@localhost:5432/ethcache</td>
    </tr>
    <tr>
        <td>TEST_DATABASE_URL</td>
        <td>False</td>
        <td nowrap>テスト用データベース URL</td>
        <td>postgresql://ethuser:ethpass@localhost:5432/ethcache_test</td>
    </tr>
    <tr>
        <td>WEB3_HTTP_PROVIDER</td>
        <td>False</td>
        <td nowrap>Web3 プロバイダー</td>
        <td>http://localhost:8545</td>
    </tr>
    <tr>
        <td>BOND_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Bond トークンの利用</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>SHARE_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Share トークンの利用</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>MEMBERSHIP_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Membership トークンの利用</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>COUPON_TOKEN_ENABLED</td>
        <td>False</td>
        <td nowrap>Coupon トークンの利用</td>
        <td>0 (not using) / 1 (using)</td>
    </tr>
    <tr>
        <td>AGENT_ADDRESS</td>
        <td>True</td>
        <td nowrap>支払代行アドレス（IbetExchangeを利用する場合にのみ設定）</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>TOKEN_LIST_CONTRACT_ADDRESS</td>
        <td>True</td>
        <td nowrap>TokenList コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>PERSONAL_INFO_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>PersonalInfo コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>PAYMENT_GATEWAY_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>PaymentGateway コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_SB_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Bond トークン用 IbetExchange コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Share トークン用 IbetExchange コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Membership トークン用 IbetExchange コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_CP_EXCHANGE_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Coupon トークン用 IbetExchange コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_ESCROW_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Ibet Escrow コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
    <tr>
        <td>IBET_SECURITY_TOKEN_ESCROW_CONTRACT_ADDRESS</td>
        <td>False</td>
        <td nowrap>Ibet Security Token Escrow コントラクトアドレス</td>
        <td>0x0000000000000000000000000000000000000000</td>
    </tr>
</table>

その他の環境変数の設定は、`app/config.py` で確認することができます。

### DB マイグレーション

[migrations/README.md](migrations/README.md) を確認してください。


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
