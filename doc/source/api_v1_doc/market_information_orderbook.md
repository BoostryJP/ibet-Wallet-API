# マーケット情報：オーダーブック

## POST: /v1/OrderBook
* 普通社債トークンのオーダーブックを返却するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/OrderBook \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{
  "token_address":"0xd950a0ba53af3f4f295500eee692598e31166ad9",
  "order_type":"buy",
  "account_address":"0x865de50bb0f21c3f318b736c04d2b6ff7dea3bfd"
}'
```

### In
```json
{
  "token_address":"0xd950a0ba53af3f4f295500eee692598e31166ad9",
  "order_type":"buy",
  "account_address":"0x865de50bb0f21c3f318b736c04d2b6ff7dea3bfd"
}
```
* `token_address` : トークンアドレス
* `order_type` : 注文種別（buy/sell）　※buyを指定すると売り注文の一覧が返される。
* `account_address` : 注文実行者のアドレスを指定する。

#### validation
```py
{
  'account_address': {
    'type': 'string'
  },
  'token_address': {
    'type': 'string',
    'empty': False,
    'required': True
  },
  'order_type': {
    'type': 'string',
    'empty': False,
    'required': True,
    'allowed': ['buy', 'sell']
  },
}
```

### Out

#### Status: 200 OK
* 正常時

```json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "order_id": 1,
            "price": 1000,
            "amount": 1000000,
            "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
        }
    ]
}
```
* `order_id` : 注文ID
* `price` : 注文単価
* `amount` : 注文数量
* `account_address` : 注文実行者のアカウントアドレス

#### Status: 400 Bad Request
* 入力値エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```


## POST: /v1/Membership/OrderBook
* 会員権トークンのオーダーブックを返却するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Membership/OrderBook \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{
  "token_address":"0xd950a0ba53af3f4f295500eee692598e31166ad9",
  "order_type":"buy",
  "account_address":"0x865de50bb0f21c3f318b736c04d2b6ff7dea3bfd"
}'
```

### In
```json
{
  "token_address":"0xd950a0ba53af3f4f295500eee692598e31166ad9",
  "order_type":"buy",
  "account_address":"0x865de50bb0f21c3f318b736c04d2b6ff7dea3bfd"
}
```
* `token_address` : トークンアドレス
* `order_type` : 注文種別（buy/sell）　※buyを指定すると売り注文の一覧が返される。
* `account_address` : 注文実行者のアドレスを指定する。

#### validation
```py
{
  'account_address': {
    'type': 'string'
  },
  'token_address': {
    'type': 'string',
    'empty': False,
    'required': True
  },
  'order_type': {
    'type': 'string',
    'empty': False,
    'required': True,
    'allowed': ['buy', 'sell']
  },
}
```

### Out

#### Status: 200 OK
* 正常時

```json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "order_id": 1,
            "price": 1000,
            "amount": 1000000,
            "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
        }
    ]
}
```
* `order_id` : 注文ID
* `price` : 注文単価
* `amount` : 注文数量
* `account_address` : 注文実行者のアカウントアドレス

#### Status: 400 Bad Request
* 入力値エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```


## POST: /v1/Coupon/OrderBook
* クーポントークンのオーダーブックを返却するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Coupon/OrderBook \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{
  "token_address":"0xd950a0ba53af3f4f295500eee692598e31166ad9",
  "order_type":"buy",
  "account_address":"0x865de50bb0f21c3f318b736c04d2b6ff7dea3bfd"
}'
```

### In
```json
{
  "token_address":"0xd950a0ba53af3f4f295500eee692598e31166ad9",
  "order_type":"buy",
  "account_address":"0x865de50bb0f21c3f318b736c04d2b6ff7dea3bfd"
}
```
* `token_address` : トークンアドレス
* `order_type` : 注文種別（buy/sell）　※buyを指定すると売り注文の一覧が返される。
* `account_address` : 注文実行者のアドレスを指定する。

#### validation
```py
{
  'account_address': {
    'type': 'string'
  },
  'token_address': {
    'type': 'string',
    'empty': False,
    'required': True
  },
  'order_type': {
    'type': 'string',
    'empty': False,
    'required': True,
    'allowed': ['buy', 'sell']
  },
}
```

### Out

#### Status: 200 OK
* 正常時

```json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "order_id": 1,
            "price": 1000,
            "amount": 1000000,
            "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
        }
    ]
}
```
* `order_id` : 注文ID
* `price` : 注文単価
* `amount` : 注文数量
* `account_address` : 注文実行者のアカウントアドレス

#### Status: 400 Bad Request
* 入力値エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```
