# ローカル開発環境構築（Mac）

## 前提条件

* OS:　OSX
* 以下の tmr-sc の Readme に従い、環境構築を行なっていること。
* （Pythonなどの環境構築、呼び出し先のQuorumの環境構築が事前に必要なため）
* https://github.com/N-Village/tmr-sc/blob/master/README.md

## 1. PostgreSQLインストール&設定
### 1-1. PostgreSQLインストール
* 参考：https://qiita.com/_daisuke/items/13996621cf51f835494b
* Homebrewを使用してインストール

```
$ brew install postgresql
:
:
==> /usr/local/Cellar/postgresql/9.3.4/bin/initdb /usr/local/var/postgres
==> Summary
?  /usr/local/Cellar/postgresql/9.3.4: 2921 files, 38M
```

### 1-2. 文字コードをUTF-8でデータベースの初期化

```
$ initdb /usr/local/var/postgres -E utf8
The files belonging to this database system will be owned by user "dai".
This user must also own the server process.

The database cluster will be initialized with locale "ja_JP.UTF-8".
initdb: could not find suitable text search configuration for locale "ja_JP.UTF-8"
The default text search configuration will be set to "simple".

Data page checksums are disabled.

initdb: directory "/usr/local/var/postgres" exists but is not empty
If you want to create a new database system, either remove or empty
the directory "/usr/local/var/postgres" or run initdb
with an argument other than "/usr/local/var/postgres".
```

### 1-3. インストール後の確認

* PATHの確認

```
$ which psql
/usr/bin/local/psql
```

* バージョンの確認

```
$ postgres --version
postgres (PostgreSQL) 9.3.4
```

### 1-4. PostgreSQLサーバの起動
```
$ postgres -D /usr/local/var/postgres

LOG:  listening on IPv4 address "127.0.0.1", port 5432
LOG:  listening on IPv6 address "::1", port 5432
LOG:  listening on Unix socket "/tmp/.s.PGSQL.5432"
LOG:  database system was shut down at 2019-01-31 10:23:23 JST
LOG:  database system is ready to accept connections
```

### 1-5. psql -lでデータベース一覧を取得

* データベースの一覧が取得できたら完了。

```
$ psql -l
                               List of databases
   Name    |  Owner  | Encoding |   Collate   |    Ctype    | Access privileges 
-----------+---------+----------+-------------+-------------+-------------------
 ethcache  | ethuser | UTF8     | ja_JP.UTF-8 | ja_JP.UTF-8 | 
 postgres  | [user]  | UTF8     | ja_JP.UTF-8 | ja_JP.UTF-8 | 
 template0 | [user]  | UTF8     | ja_JP.UTF-8 | ja_JP.UTF-8 | =c/[user] + [user] =CTc/[user] 
 template1 | [user]  | UTF8     | ja_JP.UTF-8 | ja_JP.UTF-8 | =c/[user] + [user] =CTc/[user] 
(4 rows)
```

### 1-6. DBの置き場所を環境変数の設定

* .bash_profileに以下の記述を追加

```:.bash_profile
# PostgreSQL設定（DBの置き場所）
export PGDATA=/usr/local/var/postgres
```



### 1-7. Roleの作成
* データベースのユーザ（Role）を作成する。

```
$ sudo su - postgres
$ psql
postgres=# CREATE ROLE ethuser LOGIN CREATEDB PASSWORD 'ethpass';
CREATE ROLE
```

### 1-8. Databaseの作成
* データベースを作成する。データベースのオーナーは先程作ったロールを設定する。

```
postgres=# CREATE DATABASE ethcache OWNER ethuser;
CREATE DATABASE
```

### 1-9. クライアント認証の設定
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


### 1-10. リモート接続の設定
* postgresユーザで以下のように設定変更する。

```
$ vim /etc/postgresql/9.6/main/postgresql.conf
...

listen_addresses = '*'

...
```

### 1-11. ユーザログイン疎通
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
* 必要なパッケージが指定されたバージョンで入っていることを確認するためには、以下のコマンドを用いる

```
$ pip list
```

## 3. アプリケーションの実行

* PostgreSQLサーバが起動している状態で、以下のコマンドを実行する
* API Server is starting というメッセージが表示されたら、起動成功

```
$ cd tmr-node
$ ./bin/run.sh start

 [73139] [INFO] API Server is starting [in / * /tmr-node/app/main.py:31]
```

## 4. アプリケーションのテスト

* テスト実行はpytestで実行する。

### 4-1. 全体テストの実施
* テストコードを `tests/` の中に格納して、`tests`が存在するディレクトリで以下を実行する。
* 以下は、ディレクトリ配下のテストを全て実行するコマンド。

```
$ py.test app/tests/
```

* Warningの出力をさせたくない場合は、以下のオプションをつける。

```
$ py.test app/tests/ --disable-pytest-warnings
```

### 4-2. 部分テストの実施

* モジュールを指定したい場合、以下のようなコマンドで実行
* `--pdb`は、デバックを呼び出すオプション
* `-v`はテスト詳細を表示するオプション

```
$ py.test tests/[テストするモジュール名].py  [-—pdb] [-v] 
```

* メソッドまで指定したい場合、以下のようなコマンドで実行

```
$ pytest tests/[テストするモジュール名].py -k [テストするメソッド名]  [-—pdb] [-v] 
```

### 4-3. （参考）pdbを用いたデバッグ

* pdbを用いたデバッグを行う際は、以下のページを参考
* https://docs.python.jp/3/library/pdb.html

### 4-4. (参考)postmanを用いたREST APIの動作確認

* ダウンロード　→　https://www.getpostman.com/
* 参考　→　https://www.webprofessional.jp/master-api-workflow-postman/

