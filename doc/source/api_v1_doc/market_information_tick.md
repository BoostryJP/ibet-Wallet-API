# マーケット情報：歩み値

## POST: /v1/Tick

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Tick \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{  
   "address_list":["0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}'
```

### In
```json
{  
   "address_list":["0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}
```
* `address_list` : トークンアドレスのリスト　※複数のトークンの現在値を一度に参照することができる。

#### validation
```py
{
  'address_list': {
    'type': 'list',
    'empty': False,
    'required': True,
    'schema': {
      'type': 'string',
      'required': True,
      'empty': False,
    }
  }
}
```

### Out

#### Status: 200 OK
* 正常時

``` json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "token_address": "0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72",
            "tick": [
                {
                    "block_timestamp": "2019/01/30 19:40:57",
                    "buy_address": "0x250cfb552d6916358b1Ac4c54238049bb47E3BC2",
                    "sell_address": "0x2D67e48804Cf2112094ECbEcDA6D92b0e2e6AF0A",
                    "order_id": 0,
                    "agreement_id": 0,
                    "price": 100,
                    "amount": 1
                },
                {
                    "block_timestamp": "2019/01/30 19:40:59",
                    "buy_address": "0x250cfb552d6916358b1Ac4c54238049bb47E3BC2",
                    "sell_address": "0x2D67e48804Cf2112094ECbEcDA6D92b0e2e6AF0A",
                    "order_id": 0,
                    "agreement_id": 1,
                    "price": 100,
                    "amount": 1
                }
            ]
        },
        {
            "token_address": "0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415",
            "tick": []
        }
    ]
}
```
* `token_address` : トークンアドレス
* `tick` : 歩み値のリスト。約定日時の新しい順。
  * `block_timestamp` : ブロックタイムスタンプ。約定日時と同義。
  * `buy_address` : 買注文者のアカウントアドレス。
  * `sell_address` : 売注文者のアカウントアドレス。
  * `order_id` : 注文ID
  * `agreement_id` : 約定ID
  * `price` : 約定単価
  * `amount` : 約定数量

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


## POST: /v1/Membership/Tick

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Membership/Tick \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{  
   "address_list":["0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}'
```

### In
```json
{  
   "address_list":["0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}
```
* `address_list` : トークンアドレスのリスト　※複数のトークンの現在値を一度に参照することができる。

#### validation
```py
{
  'address_list': {
    'type': 'list',
    'empty': False,
    'required': True,
    'schema': {
      'type': 'string',
      'required': True,
      'empty': False,
    }
  }
}
```

### Out

#### Status: 200 OK
* 正常時

``` json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "token_address": "0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72",
            "tick": [
                {
                    "block_timestamp": "2019/01/30 19:40:57",
                    "buy_address": "0x250cfb552d6916358b1Ac4c54238049bb47E3BC2",
                    "sell_address": "0x2D67e48804Cf2112094ECbEcDA6D92b0e2e6AF0A",
                    "order_id": 0,
                    "agreement_id": 0,
                    "price": 100,
                    "amount": 1
                },
                {
                    "block_timestamp": "2019/01/30 19:40:59",
                    "buy_address": "0x250cfb552d6916358b1Ac4c54238049bb47E3BC2",
                    "sell_address": "0x2D67e48804Cf2112094ECbEcDA6D92b0e2e6AF0A",
                    "order_id": 0,
                    "agreement_id": 1,
                    "price": 100,
                    "amount": 1
                }
            ]
        },
        {
            "token_address": "0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415",
            "tick": []
        }
    ]
}
```
* `token_address` : トークンアドレス
* `tick` : 歩み値のリスト。約定日時の新しい順。
  * `block_timestamp` : ブロックタイムスタンプ。約定日時と同義。
  * `buy_address` : 買注文者のアカウントアドレス。
  * `sell_address` : 売注文者のアカウントアドレス。
  * `order_id` : 注文ID
  * `agreement_id` : 約定ID
  * `price` : 約定単価
  * `amount` : 約定数量

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

## POST: /v1/Coupon/Tick

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Coupon/Tick \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{  
   "address_list":["0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}'
```

### In
```json
{  
   "address_list":["0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}
```
* `address_list` : トークンアドレスのリスト　※複数のトークンの現在値を一度に参照することができる。

#### validation
```py
{
  'address_list': {
    'type': 'list',
    'empty': False,
    'required': True,
    'schema': {
      'type': 'string',
      'required': True,
      'empty': False,
    }
  }
}
```

### Out

#### Status: 200 OK
* 正常時

``` json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "token_address": "0xcBCD0c901B36a00DDa92C5a6f85547eAE255CC72",
            "tick": [
                {
                    "block_timestamp": "2019/01/30 19:40:57",
                    "buy_address": "0x250cfb552d6916358b1Ac4c54238049bb47E3BC2",
                    "sell_address": "0x2D67e48804Cf2112094ECbEcDA6D92b0e2e6AF0A",
                    "order_id": 0,
                    "agreement_id": 0,
                    "price": 100,
                    "amount": 1
                },
                {
                    "block_timestamp": "2019/01/30 19:40:59",
                    "buy_address": "0x250cfb552d6916358b1Ac4c54238049bb47E3BC2",
                    "sell_address": "0x2D67e48804Cf2112094ECbEcDA6D92b0e2e6AF0A",
                    "order_id": 0,
                    "agreement_id": 1,
                    "price": 100,
                    "amount": 1
                }
            ]
        },
        {
            "token_address": "0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415",
            "tick": []
        }
    ]
}
```
* `token_address` : トークンアドレス
* `tick` : 歩み値のリスト。約定日時の新しい順。
  * `block_timestamp` : ブロックタイムスタンプ。約定日時と同義。
  * `buy_address` : 買注文者のアカウントアドレス。
  * `sell_address` : 売注文者のアカウントアドレス。
  * `order_id` : 注文ID
  * `agreement_id` : 約定ID
  * `price` : 約定単価
  * `amount` : 約定数量

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
