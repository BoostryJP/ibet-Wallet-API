# 注文一覧・約定一覧

## POST: /v1/OrderList/

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/OrderList/ \
  -H 'Content-Type: application/json' \
  -H 'cache-control: no-cache' \
  -d '{
    "account_address_list": [
        "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
        "0x5c572fA7690a2a2834A06427Ca2F73959A0c891e"
    ]
}'
```

### In
```json
{
    "account_address_list": [
        "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
        "0x5c572fA7690a2a2834A06427Ca2F73959A0c891e"
    ]
}
```
* `account_address_list` : アカウントアドレスのリスト。※複数のアカウントの保有一覧をまとめて返すことが出来る。

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
    "data": {
        "order_list": [
            {
                "token": {
                    "token_address": "0x6F9a2C569cdeADb95472CC26EE0D9e73df4c186D",
                    "token_template": "IbetMembership",
                    "company_name": "株式会社DEMO",
                    "name": "会員権１",
                    "symbol": "TESTMEM",
                    "total_supply": 1000000,
                    "details": "会員権の詳細内容",
                    "return_details": "リターンの詳細内容",
                    "expiration_date": "20190331",
                    "memo": "メモ欄",
                    "transferable": true,
                    "status": true,
                    "image_url": [
                        {
                            "type": "small",
                            "url": ""
                        },
                        {
                            "type": "medium",
                            "url": "https://xxx.co.jp"
                        },
                        {
                            "type": "large",
                            "url": ""
                        }
                    ]
                },
                "order": {
                    "order_id": 1,
                    "amount": 1000000,
                    "price": 1000,
                    "is_buy": false,
                    "canceled": false
                },
                "sort_id": 2
            },
            {
                "token": {
                    "token_address": "0x9E5D93cE6A86a8254A7a1b67Eb03769D46359dDd",
                    "token_template": "IbetCoupon",
                    "company_name": "株式会社DEMO",
                    "name": "クーポン１",
                    "symbol": "TESTCP1",
                    "total_supply": 1000000,
                    "details": "クーポンの詳細内容",
                    "return_details": "リターンの詳細内容",
                    "expiration_date": "20190331",
                    "memo": "メモ欄",
                    "transferable": true,
                    "status": true,
                    "image_url": [
                        {
                            "type": "small",
                            "url": ""
                        },
                        {
                            "type": "medium",
                            "url": "https://hoge.hoge.co.jp"
                        },
                        {
                            "type": "large",
                            "url": ""
                        }
                    ],
                    "payment_method_credit_card": true,
                    "payment_method_bank": true,
                    "contact_information": "問い合わせ先の内容",
                    "privacy_policy": "プライバシーポリシーの内容"
                },
                "order": {
                    "order_id": 1,
                    "amount": 1000000,
                    "price": 1000,
                    "is_buy": false,
                    "canceled": false
                },
                "sort_id": 4
            }
        ],
        "settlement_list": [
            {
                "token": {
                    "token_address": "0xe761C100C88607B2f6B43647A9CA114e24d0b98a",
                    "token_template": "IbetCoupon",
                    "company_name": "",
                    "name": "SEINO_TEST_TOKEN",
                    "symbol": "SEINO",
                    "total_supply": 2,
                    "details": "details",
                    "return_details": "return_details",
                    "expiration_date": "20181010",
                    "memo": "memo",
                    "transferable": true,
                    "status": true,
                    "image_url": [
                        {
                            "type": "small",
                            "url": ""
                        },
                        {
                            "type": "medium",
                            "url": ""
                        },
                        {
                            "type": "large",
                            "url": ""
                        }
                    ],
                    "payment_method_credit_card": true,
                    "payment_method_bank": true
                },
                "agreement": {
                    "exchange_address": "0xd32dBF7bE973B860A9EFc33764fE40bd113C4807",
                    "order_id": 0,
                    "agreement_id": 0,
                    "amount": 1,
                    "price": 100,
                    "is_buy": true,
                    "canceled": false
                },
                "sort_id": 3
            }
        ],
        "complete_list": [
            {
                "token": {
                    "token_address": "0xe761C100C88607B2f6B43647A9CA114e24d0b98a",
                    "token_template": "IbetCoupon",
                    "company_name": "",
                    "name": "SEINO_TEST_TOKEN",
                    "symbol": "SEINO",
                    "total_supply": 2,
                    "details": "details",
                    "return_details": "return_details",
                    "expiration_date": "20181010",
                    "memo": "memo",
                    "transferable": true,
                    "status": true,
                    "image_url": [
                        {
                            "type": "small",
                            "url": ""
                        },
                        {
                            "type": "medium",
                            "url": ""
                        },
                        {
                            "type": "large",
                            "url": ""
                        }
                    ],
                    "payment_method_credit_card": true,
                    "payment_method_bank": true
                },
                "agreement": {
                    "exchange_address": "0xd32dBF7bE973B860A9EFc33764fE40bd113C4807",
                    "order_id": 0,
                    "agreement_id": 1,
                    "amount": 1,
                    "price": 100,
                    "is_buy": true
                },
                "settlement_timestamp": "2017/04/10 10:00:00",
                "sort_id": 4
            }
        ]
    }
}
```
* `order_list` : 注文中一覧
  * `order` : 注文情報
    * `order_id` : 注文ID
    * `amount` : 注文数量
    * `price` : 注文単価
    * `is_buy` : 売買区分（`true`:買い、`false`:売り）
    * `canceled` : 取消済（`true`:取消済、`false`:未取消）
* `settlement_list` : 決済中一覧。約定済、決済承認待ち（約定代金の入金待ち）の状態。
  * `agreement` : 約定情報
    * `exchange_address` : DEXアドレス
    * `order_id` : 注文ID
    * `agreement_id` : 約定ID
    * `amount` : 注文数量
    * `price` : 注文単価
    * `is_buy` : 売買区分（`true`:買い、`false`:売り）
* `complete_list` : 決済済一覧
  * `agreement` : ※`settlement_list`と同じ
* `token` : トークンの属性情報
* `settlement_timestamp` : 決済日時（受渡日時）
* `sort_id` : ソート用のID。注文(order)、約定(agreement)のそれぞれで古いものから順に採番されている。

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
