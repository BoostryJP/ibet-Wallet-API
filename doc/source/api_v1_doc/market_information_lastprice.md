# マーケット情報：現在値

## POST: /v1/StraightBond/LastPrice
* 普通社債トークンの現在値を返却するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/StraightBond/LastPrice \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{  
   "address_list":["0xd950a0ba53af3f4f295500eee692598e31166ad9","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}'
```

### In
```json
{  
  "address_list":["0xd950a0ba53af3f4f295500eee692598e31166ad9","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
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

```json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "token_address": "0xd950a0ba53af3f4f295500eee692598e31166ad9",
            "last_price": 1000
        },
        {
            "token_address": "0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415",
            "last_price": 0
        }
    ]
}
```

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

## POST: /v1/Membership/LastPrice
* 会員権トークンの現在値を返却するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Membership/LastPrice \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{  
   "address_list":["0xd950a0ba53af3f4f295500eee692598e31166ad9","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}'
```

### In
```json
{  
  "address_list":["0xd950a0ba53af3f4f295500eee692598e31166ad9","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
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

```json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "token_address": "0xd950a0ba53af3f4f295500eee692598e31166ad9",
            "last_price": 1000
        },
        {
            "token_address": "0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415",
            "last_price": 0
        }
    ]
}
```

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


## POST: /v1/Coupon/LastPrice
* クーポントークンの現在値を返却するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Coupon/LastPrice \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{  
   "address_list":["0xd950a0ba53af3f4f295500eee692598e31166ad9","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
}'
```

### In
```json
{  
  "address_list":["0xd950a0ba53af3f4f295500eee692598e31166ad9","0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415"]
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

```json
{
    "meta": {
        "code": 200,
        "message": "OK"
    },
    "data": [
        {
            "token_address": "0xd950a0ba53af3f4f295500eee692598e31166ad9",
            "last_price": 1000
        },
        {
            "token_address": "0x9bf94e7c541e42b4b4362522fbcb6fc0b173e415",
            "last_price": 0
        }
    ]
}
```

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
