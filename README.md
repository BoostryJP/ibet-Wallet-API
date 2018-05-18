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

## 2. 開発環境用の Quorum(Ethereum) の構築
* Dockerコンテナを利用して、ローカルの開発環境にQuorumクラスタを構築する。
* https://github.com/N-Village/tmr-docker の、`quorum-dev`を利用する。

  1. docker-ceのインストール
  2. docker-composeのインストール
  3. tmr-dockerリポジトリをチェックアウト
  4. ./quorum-dev/ に移動
  5. docker-compose up -d でクラスタが起動する。
  6. 起動後の状態は以下のような状態になる（※ContainerID等は異なる）
  7. `geth attach http://localhost:8545` で`quorum-dev_validator-0_1`に接続できる。
  8. テスト用アカウントして、新規のアカウントを4つ（deployer, issuer, agent, trader）作成する。 `personal.newAccount("password")` で作成する。

```
CONTAINER ID        IMAGE                          COMMAND                  CREATED             STATUS              PORTS                                                                         NAMES
1f51a0df93dc        quorum-dev                     "/bin/sh -c 'mkdir -…"   2 weeks ago         Up 2 days           8546/tcp, 30303-30304/udp, 0.0.0.0:8547->8545/tcp, 0.0.0.0:30305->30303/tcp   quorum-dev_validator-2_1
9c5d149dd582        quay.io/amis/ethstats:latest   "npm start"              2 weeks ago         Up 2 days           0.0.0.0:3000->3000/tcp                                                        quorum-dev_eth-stats_1
56fc9f3a0d72        quorum-dev                     "/bin/sh -c 'mkdir -…"   2 weeks ago         Up 2 days           8546/tcp, 30303-30304/udp, 0.0.0.0:8548->8545/tcp, 0.0.0.0:30306->30303/tcp   quorum-dev_validator-3_1
a4cfd7c80e14        quorum-dev                     "/bin/sh -c 'mkdir -…"   2 weeks ago         Up 2 days           0.0.0.0:8545->8545/tcp, 0.0.0.0:30303->30303/tcp, 8546/tcp, 30303-30304/udp   quorum-dev_validator-0_1
a3b215425e01        quorum-dev                     "/bin/sh -c 'mkdir -…"   2 weeks ago         Up 2 days           8546/tcp, 30303-30304/udp, 0.0.0.0:8546->8545/tcp, 0.0.0.0:30304->30303/tcp   quorum-dev_validator-1_1
```
