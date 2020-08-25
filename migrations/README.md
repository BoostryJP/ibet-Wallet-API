# メンテナンス方法

## バージョン管理

バージョン管理は `version_control` テーブルで行われる。

### バージョン管理テーブルの新規作成
```sh
% python manage.py version_control
# migrate_version テーブルが作られる
```

### 現在のバージョンの確認
```sh
% migrate version .
```

## マイグレーション実行

### アップグレード
```sh
% python manage.py upgrade    
0 -> 1... 
done
```

### ダウングレード
```sh
 % python manage.py downgrade 0
1 -> 0... 
done
```

## スクリプトの記述方法

### テーブル新規作成
以下のコマンドを実行するとマイグレーションスクリプトが新規作成される。
* テーブル新規作成のためのスクリプトは `create_<TBL名>` とする。
```sh
% python manage.py script "create agreement"
# agreement テーブルを新規作成する例
# versions/001_create_agreement.pyが作成される
```

テーブル新規追加のスクリプトは以下のような構造で記述する。upgrade時に既にテーブルが存在する場合、WARNINGを出力するようにする。

```python
# -*- coding: utf-8 -*-
import logging
from datetime import datetime

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


# Table定義
meta = MetaData()
table = Table(
    "agreement", meta,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("exchange_address", String(256), primary_key=True),
    Column("order_id", BigInteger, primary_key=True),
    Column("agreement_id", BigInteger, primary_key=True),
    Column("unique_order_id", String(256), index=True),
    Column("buyer_address", String(256), index=True),
    Column("seller_address", String(256), index=True),
    Column("counterpart_address", String(256)),
    Column("amount", BigInteger),
    Column("status", Integer),
    Column("settlement_timestamp", DateTime, default=None),
    Column("created", DateTime, default=datetime.utcnow),
    Column("modified", DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
)


# Upgrade
def upgrade(migrate_engine):
    meta.bind = migrate_engine
    try:
        table.create()
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)


# Downgrade
def downgrade(migrate_engine):
    meta.bind = migrate_engine
    table.drop()

```

### カラム追加
テーブル新規追加のスクリプトは以下のような構造で記述する。

```python
# -*- coding: utf-8 -*-
import logging

from sqlalchemy import *
from sqlalchemy.exc import ProgrammingError
from migrate import *


meta = MetaData()

def upgrade(migrate_engine):
    meta.bind = migrate_engine

    listing_table = Table("listing", meta)
    col = Column("owner_address", String(256))
    try:
        col.create(listing_table)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)

def downgrade(migrate_engine):
    meta.bind = migrate_engine

    listing_table = Table("listing", meta)
    try:
        Column("owner_address").drop(listing_table)
    except sqlalchemy.exc.ProgrammingError as err:
        logging.warning(err)

```

### カラム修正
```python
# -*- coding: utf-8 -*-
from sqlalchemy import *
from migrate import *

meta = MetaData()


def upgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)
    order.c.token_address.alter(type=String(42), index=True)
    order.c.exchange_address.alter(type=String(42), index=True)
    order.c.account_address.alter(type=String(42))
    order.c.agent_address.alter(type=String(42))

def downgrade(migrate_engine):
    meta.bind = migrate_engine

    order = Table("order", meta, autoload=True)
    order.c.token_address.alter(type=String(256), index=True)
    order.c.exchange_address.alter(type=String(256), index=True)
    order.c.account_address.alter(type=String(256))
    order.c.agent_address.alter(type=String(256))

```