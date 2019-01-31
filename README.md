# tmr-node

# ローカル開発環境構築（Mac）

## 前提条件

* 以下の tmr-sc の Readme に従い、環境構築を行なっていること。
* （Pythonなどの環境構築、呼び出し先のQuorumの環境構築が事前に必要なため）
* https://github.com/N-Village/tmr-sc/blob/master/README.md

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

## 2. 依存パッケージのインストール
* 依存パッケージをpipでインストールする。

```
$ cd tmr-node
$ pip install -r requirements.txt
```

* 動作確認
* 必要なパッケージが指定したバージョンで入っていることを確認

```
$ pip list

$ pip list
Package           Version  
----------------- ---------
asn1crypto        0.24.0   
astroid           2.1.0    
atomicwrites      1.2.1    
attrdict          2.0.0    
attrs             18.2.0   
** 省略　**
eth-abi           1.1.1    
eth-account       0.2.2    
eth-hash          0.1.0    
eth-keyfile       0.5.0    
eth-keys          0.2.0b3  
eth-rlp           0.1.2    
eth-tester        0.1.0b11 
eth-utils         1.0.1    
ethereum          2.3.0    
falcon            1.4.1    
future            0.16.0   
gunicorn          19.7.1   
** 省略　**
wrapt             1.11.1
```


