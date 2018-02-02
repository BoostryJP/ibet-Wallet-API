# tmr-node

# ローカル開発環境構築（Ubuntu）

## 1. PostgreSQLインストール&設定
### 1-1. PostgreSQLインストール
* 参考：https://qiita.com/eighty8/items/82063beab09ab9e41692

```
$ sudo sh -c "echo 'deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main' > /etc/apt/sources.list.d/pgdg.list"
$ wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
```

* パッケージをアップデートしてインストール。

```
$ sudo apt-get update
$ sudo apt-get install postgresql-9.6
```

* インストール後の確認

```
$ which psql
/usr/bin/psql
```

### 1-2. Roleの作成
* データベースのユーザ（Role）を作成する。

```
$ sudo su - postgres
$ psql
postgres=# CREATE ROLE ethuser LOGIN CREATEDB PASSWORD 'ethpass';
CREATE ROLE
```

### 1-3. Databaseの作成
* データベースを作成する。データベースのオーナーは先程作ったロールを設定する。

```
postgres=# CREATE DATABASE ethcache OWNER ethuser;
CREATE DATABASE
```

### 1-4. クライアント認証の設定
* postgresユーザで以下のように設定を変更する。

```
$ vim /etc/postgresql/9.6/main/pg_hba.conf
...

# Database administrative login by Unix domain socket
local   all             postgres                                peer

# TYPE  DATABASE        USER            ADDRESS                 METHOD

# "local" is for Unix domain socket connections only
local   all             all                                     trust
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
host    all             postgres        0.0.0.0/0               reject
host    all             all             0.0.0.0/0               md5
# IPv6 local connections:
host    all             all             ::1/128                 md5

...
```

* postgresqlを再起動する。（※補足：停止する場合は``stop``）

```
$ /etc/init.d/postgresql restart
[ ok ] Restarting postgresql (via systemctl): postgresql.service.
```


### 1-5. リモート接続の設定
* postgresユーザで以下のように設定変更する。

```
$ vim /etc/postgresql/9.6/main/postgresql.conf
...

listen_addresses = '*'

...
```

### 1-6. ユーザログイン疎通
* postgresユーザ（※OSユーザ）以外でDBにログインしてみる。ログアウトはCtl+zなど。

```
$ psql --username=ethuser --password --dbname=ethcache
```

## 2. Ethereumインストール&設定
### 2-1. Ethereumインストール
* 以下のコマンドでインストールを行う。
```
$ sudo apt-get install software-properties-common
$ sudo add-apt-repository -y ppa:ethereum/ethereum
$ sudo apt-get update
$ sudo apt-get install ethereum
```

* バージョンの確認。
```
$ geth version
Geth
Version: 1.7.3-stable
Git Commit: 4bb3c89d44e372e6a9ab85a8be0c9345265c763a
Architecture: amd64
Protocol Versions: [63 62]
Network Id: 1
Go Version: go1.9
Operating System: linux
GOPATH=
GOROOT=/usr/lib/go-1.9
```

### 2-2. private net を作成
```
$ mkdir ~/eth_private
$ cd eth_private
```

* genesis.jsonを作成する。
```
$ cat genesis.json
{
  "config": {
        "chainId": 15,
        "homesteadBlock": 0,
        "eip155Block": 0,
        "eip158Block": 0
    },
  "alloc"      : {},
  "coinbase"   : "0x0000000000000000000000000000000000000000",
  "difficulty" : "0x20000",
  "extraData"  : "",
  "gasLimit"   : "0x2fefd8",
  "nonce"      : "0x0000000000000042",
  "mixhash"    : "0x0000000000000000000000000000000000000000000000000000000000000000",
  "parentHash" : "0x0000000000000000000000000000000000000000000000000000000000000000",
  "timestamp"  : "0x00"
}
```

* 初期化（genesis blockの作成）
```
$ geth --datadir ~/eth_private init ~/eth_private/genesis.json
```

* 起動
```
$ geth --datadir ~/eth_private --networkid 15
```

* コンソール立ち上げ
```
$ geth --datadir ~/eth_private --networkid 15 console
```

### 2-3. アカウント作成
* 新しいアカウントを作成する。
```
> personal.newAccount("password")
"0x7ae52ca0c275982bb1c27e7ef5a6e920aad655c2"
```

* アカウントの一覧を確認。
```
> eth.accounts
["0x7ae52ca0c275982bb1c27e7ef5a6e920aad655c2"]
```

* coinbaseを確認。
```
> eth.coinbase
"0x7ae52ca0c275982bb1c27e7ef5a6e920aad655c2"
```

### 2-4. マイニング実行
* 以下のコマンドを実行する。
```
> miner.start()
INFO [01-23|09:53:31] Updated mining threads                   threads=0
INFO [01-23|09:53:31] Transaction pool price threshold updated price=18000000000
INFO [01-23|09:53:31] Starting mining operation
INFO [01-23|09:53:31] Commit new mining work                   number=1 txs=0 uncles=0 elapsed=252.509µs
null
> INFO [01-23|09:53:35] Generating DAG in progress               epoch=0 percentage=0 elapsed=3.180s
INFO [01-23|09:53:38] Generating DAG in progress               epoch=0 percentage=1 elapsed=6.343s
INFO [01-23|09:53:42] Generating DAG in progress               epoch=0 percentage=2 elapsed=9.576s
INFO [01-23|09:53:45] Generating DAG in progress               epoch=0 percentage=3 elapsed=12.738s
INFO [01-23|09:53:48] Generating DAG in progress               epoch=0 percentage=4 elapsed=15.946s
INFO [01-23|09:53:51] Generating DAG in progress               epoch=0 percentage=5 elapsed=19.051s
（※以下省略）
```

* マイニングを停止する。
```
> miner.stop()
```

* 残高確認（Wei換算）
```
> eth.getBalance(eth.accounts[0])
```

* 残高確認（Ether換算）
```
> web3.fromWei(eth.getBalance(eth.accounts[0]),"ether")
```

### 2-5. RPC起動
* RPCを起動する。
```
geth --datadir ~/eth_private --networkid 15 --cache=512 --rpc --rpcaddr "0.0.0.0" --rpcport 8545 --rpccorsdomain "*" --rpcapi "admin,db,eth,debug,miner,net,shh,txpool,personal,web3" console
```

## 3. その他依存ライブラリ
* solcをインストール
```
$ sudo apt-get install solc
```

* pyethereumをインストール
```
$ sudo apt-get install libssl-dev build-essential automake pkg-config libtool libffi-dev libgmp-dev libyaml-cpp-dev
$ git clone https://github.com/ethereum/pyethereum/
$ cd pyethereum
$ python setup.py install
```
