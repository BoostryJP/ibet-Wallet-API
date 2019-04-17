# stripe

## POST: /v1/Stripe/CreateAccount/
* stripeのconnectアカウントを作成する。
* すでにaccount_addressに登録されたconnectアカウントが存在する場合は、connectアカウントのupdateを行う。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Stripe/CreateAccount/ \
  -H 'Content-Type: application/json' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache' \
  -d '{
    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "account_token":  "ct_1EPLU9HgQLLPjBO2760HyH5v"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "account_token": "ct_1EPLU9HgQLLPjBO2760HyH5v"
}
```    

* `account_address`: ウォレットのアカウントアドレス。
* `account_token` : stripeのアカウントトークン。あらかじめクライアント側にて`https://api.stripe.com/v1/tokens`を呼び出した上で発行する。

#### validation
```py
{
  'account_address': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
  },
  'account_token': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
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
        }
    ]
}
```
* `xxxxx` : response不要？

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

#### Status: 405 Bad Request
* 自サーバー起因でstripeからのエラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

#### Status: 500 Server Error
* 自サーバー起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "server error",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```

#### Status: 505 Server Error
* stripe側起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

## POST: /v1/Stripe/CreateExternalAccount/
* stripeのconnectアカウントにひもづく外部口座（銀行口座）を登録する。
* account_addressに登録されたconnectアカウントがない場合は新規で作成する。すでに存在する場合は、accout_addressに対して銀行口座を登録する。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Stripe/CreateExternalAccount/ \
  -H 'Content-Type: application/json' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache' \
  -d '{
    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "bank_token":  "btok_1EQ4ooHgQLLPjBO21MKfT6A4"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "bank_token": "ct_1EPLU9HgQLLPjBO2760HyH5v"
}
```    

* `account_address`: ウォレットのアカウントアドレス。
* `bank_token` : stripeの銀行口座トークン。あらかじめクライアント側にて`https://api.stripe.com/v1/tokens`を呼び出した上で発行する。

#### validation
```py
{
  'account_address': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
  },
  'bank_token': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
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
        }
    ]
}
```
* `xxxxx` : response不要？

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

#### Status: 405 Bad Request
* 自サーバー起因でstripeからのエラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

#### Status: 500 Server Error
* 自サーバー起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "server error",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```

#### Status: 505 Server Error
* stripe側起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

## POST: /v1/Stripe/GetAccountInfo/
* アドレスに紐付くstripeのidやアカウントの情報を取得する

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Stripe/GetAccountInfo/\
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -d '{
    "account_address_list": [
        "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
        "0x5c572fA7690a2a2834A06427Ca2F73959A0c891e"
    ]
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "account_address_list": [
        "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
        "0x5c572fA7690a2a2834A06427Ca2F73959A0c891e"
    ]
}
```
* `account_address_list` : アカウントアドレスのリスト。※複数のアカウントの情報をまとめて返すことが出来る。

#### validation
```py
{
  'account_address_list': {
    'type': 'list',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
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
            "stripe_account_info_list": [
                {
                    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
                    "stripe_account_id": "acct_1EPLUEFV9leziGQ8",
                    "stripe_customer_id": "cus_ErghPzTI68hTis",
                    "verification_status": "Pending",
                },
                {
                    "account_address": "0x5c572fA7690a2a2834A06427Ca2F73959A0c891e",
                    "stripe_account_id": null,
                    "stripe_customer_id": null,
                    "verification_status": null,
                }
            ]
        }
    ]
}
```
* `stripe_account_info_list` : アドレスに紐付くstripeの情報のリスト
  * `account_address`: リクエストに含まれるアカウントアドレス
  * `stripe_account_id`: アカウントアドレスに紐付くstripeのconnectアカウントid
  * `stripe_customer_id`: アカウントアドレスに紐付くstripeのcustomer id
  * `verification_status`: 個人情報承認ステータス。`Pending` or `Verified` or `Unverified`



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

#### Status: 405 Bad Request
* 自サーバー起因でstripeからのエラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

#### Status: 500 Server Error
* 自サーバー起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "server error",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```

#### Status: 505 Server Error
* stripe側起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```
## POST: /v1/Stripe/CreateCustomer/
* stripeのカスタマーの登録
* すでにaccount_addressに登録されたcustomerが存在する場合は、customerのupdateを行う。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Stripe/CreateCustomer/\
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -d '{
    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "card_token": "tok_1ENy48HgQLLPjBO2cjTJmDqT"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "account_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "card_token": "tok_1ENy48HgQLLPjBO2cjTJmDqT"
}
```
* `account_address` : ウォレットのアカウントアドレス。
* `card_token`: stripeのカードトークン。あらかじめクライアント側にて`https://api.stripe.com/v1/tokens`を呼び出した上で発行する。

#### validation
```py
{
  'account_address': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
  },
  'card_token': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
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
        }
    ]
}
```
* `xxxxx` : レスポンス不要？


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

#### Status: 405 Bad Request
* 自サーバー起因でstripeからのエラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

#### Status: 500 Server Error
* 自サーバー起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "server error",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```

#### Status: 505 Server Error
* stripe側起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```



## POST: /v1/Stripe/Charge/
* stripeのconnectアカウントに対して、決済を行う。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/v1/Stripe/Charge/ \
  -H 'Content-Type: application/json' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache' \
  -d '{
    "order_id": 1,
    "agreement_id": 4,
    "buyer_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "seller_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "amount": 2000
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "order_id": 1,
    "agreement_id": 4,
    "buyer_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "seller_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
    "amount": 2000,
}
```
* `order_id`: 決済対象の注文ID
* `agremeent_id`: 決済対象の約定ID
* `buyer_address` : 買い手のアドレス
* `seller_address`: 売り手のアドレス
* `amount`: 決済金額

#### validation
```py
{
  'order_id': {
    'type': 'int',
    'schema': {'type': 'int'},
    'empty': False,
    'required': True
  },
  'buyer_address': {
    'type': 'int',
    'schema': {'type': 'int'},
    'empty': False,
    'required': True
  },
  'buyer_address': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
  },
  'seller_address': {
    'type': 'string',
    'schema': {'type': 'string'},
    'empty': False,
    'required': True
  },
  'amount': {
    'type': 'int',
    'schema': {'type': 'int'},
    'empty': False,
    'required': True
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
            "receipt_url":"https://pay.stripe.com/receipts/acct_1EMvILHgQLLPjBO2/ch_1EOHepHgQLLPjBO2HYfCJab7/rcpt_Es1ilYtQQ9dqURTJKXAH7fLRxBL7cbe"
        }
    ]
}
```
* `receipt_url` : stripeの領収書url

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

#### Status: 405 Bad Request
* 自サーバー起因でstripeからのエラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```

#### Status: 500 Server Error
* 自サーバー起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "server error",
        "description": "No JSON object could be decoded or Malformed JSON"
    }
}
```

#### Status: 505 Server Error
* stripe側起因エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Error message From Stripe(code)",
        "description": "Error description From Stripe(message)"
    }
}
```
