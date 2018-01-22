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
