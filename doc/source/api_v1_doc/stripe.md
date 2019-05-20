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
    "account_token":  "ct_1EPLU9HgQLLPjBO2760HyH5v"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "account_token": "ct_1EPLU9HgQLLPjBO2760HyH5v"
}
```    

* `account_token` : stripeのアカウントトークン。あらかじめクライアント側にて`https://api.stripe.com/v1/tokens`を呼び出した上で発行する。

#### validation
```py
{
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
    "data": 
        {
            "stripe_account_id": "acct_1EQ5b5FHt5cjdvzv"
        }
}
```
* `stripe_account_id` : stripeにて登録後のconnectアカウントid

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
    "bank_token":  "btok_1EQ4ooHgQLLPjBO21MKfT6A4"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "bank_token": "ct_1EPLU9HgQLLPjBO2760HyH5v"
}
```    

* `bank_token` : stripeの銀行口座トークン。あらかじめクライアント側にて`https://api.stripe.com/v1/tokens`を呼び出した上で発行する。

#### validation
```py
{
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
    "data": 
        {
            "stripe_account_id": "acct_1EQ5b5FHt5cjdvzv"
        }
}
```
* `stripe_account_id` : stripeにて登録後のconnectアカウントid

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
    "card_token": "tok_1ENy48HgQLLPjBO2cjTJmDqT"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "card_token": "tok_1ENy48HgQLLPjBO2cjTJmDqT"
}
```
* `card_token`: stripeのカードトークン。あらかじめクライアント側にて`https://api.stripe.com/v1/tokens`を呼び出した上で発行する。

#### validation
```py
{
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
    "data": 
        {
            "stripe_customer_id": "cus_ErghPzTI68hTis"
        }
}
```
* `stripe_customer_id` : アカウントアドレスに紐付くstripeのcustomer id


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
  http://localhost:5000/v1/Stripe/Charge/ \
  -H 'Content-Type: application/json' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache' \
  -d '{
    "order_id": 1,
    "agreement_id": 4,
    "amount": 2000,
    "exchange_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "order_id": 1,
    "agreement_id": 4,
    "amount": 2000,
    "exchange_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51"
}
```
* `order_id`: 決済対象の注文ID
* `agremeent_id`: 決済対象の約定ID
* `amount`: 決済金額
* `exchange_address`: 取引所のアドレス

#### validation
```py
{
    'order_id': {
        'type': 'integer',
        'empty': False,
        'required': True
    },
    'agreement_id': {
        'type': 'integer',
        'empty': False,
        'required': True
    },
    'amount': {
        'type': 'integer',
        'empty': False,
        'required': True
    },
    'exchange_address': {
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

* 入力値エラー時
* 約定情報に存在しない 'order_id' または 'agreement_id' を入力値として受け取った際のエラー
  
```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "The parameter "order_id" or "agreement_id" are invalid. Record not found."
    }
}
```

* 入力値エラー時
* StripeAccountテーブルに存在しないアドレスを 'buyer_address' として受け取った際のエラー

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "The parameter "buyer_address" is invalid. Record not found."
    }
}
```

* 入力値エラー時
* StripeAccountテーブルに存在しないアドレスを 'seller_address' として受け取った際のエラー
* （'seller_address' は約定情報から取得したアドレス）

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "The parameter "seller_address" is invalid. Record not found."
    }
}
```

* 入力値エラー時
* 入力された金額が約定コントラクトの約定金額と異なる際のエラー

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "The parameter "amount" is invalid."
    }
}
```

* 入力値エラー時（Stripe側のエラー）
* 指定されたStripeの顧客id `customer_id` に紐づけられているクレジットカードが有効ではない際のエラー

```json
{
  "meta": {
    "code": 60,
    "message": "Invalid Credit Card"
  }
}
```

#### Status: 403 Server Error
* 二重課金エラー時

```json
{
    "meta": {
        "code": 70,
        "message": "Double Charge",
        "description": "double charge"
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
