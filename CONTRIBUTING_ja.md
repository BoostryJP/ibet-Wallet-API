# 開発者向けドキュメント（日本語）

## 0. 開発推奨環境

* OS: macOS 10.14 (Mojave)
* PostgreSQL: 10.11
* Python: 3.6.8

## 1. PostgreSQL

* PostgreSQLをインストールする
* `ethuser`というユーザを作成し、Databaseを作成する
```
postgres=# CREATE DATABASE ethcache OWNER ethuser;
CREATE DATABASE
```

## 2. Python依存パッケージのインストール
```
$ cd ibet-Wallet-API
$ pip install -r requirements.txt
```

## 3. サーバの起動

* 環境変数の設定

```
export WORKER_COUNT=8
```

* サーバ起動
```
$ cd ibet-Wallet-API
$ ./bin/run.sh start
```

## 4. テストの実行
* テスト用のPythonパッケージをインストールする
```
$ cd ibet-Wallet-API/app/tests
$ pip install -r requirements.txt
```

* テストの実行
```
$ cd ibet-Wallet-API/
$ py.test app/tests/
```

* 部分的に実行する場合
```
$ py.test tests/[テストするモジュール名].py  [-—pdb] [-v] 
```

* テストケースを指定して実行する場合

```
$ pytest tests/[テストするモジュール名].py -k [テストするファンクション名]  [-—pdb] [-v] 
```
