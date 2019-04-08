# マーケット情報：トークン一覧

## GET: /v1/StraightBond/Contracts
* 公開中の債券トークンの一覧を返すAPI。
* 公開済み、かつ償還されていないものが一覧で返される。
* 出力リストは登録の新しい順。

### Sample
```sh
curl -X GET \
  'http://localhost:5000/v1/StraightBond/Contracts/?cursor=3&limit=1' \
  -H 'cache-control: no-cache'
```

### In
* `cursor` : 検索用のカーソルナンバー
* `limit` :　検索上限

#### validation
```py
{
        'cursor': {
            'type': 'integer',
            'coerce': int,
            'min':0,
            'required': False,
            'nullable': True,
        },
        'limit': {
            'type': 'integer',
            'coerce': int,
            'min':0,
            'required': False,
            'nullable': True,
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
            "id": 0,
            "token_address": "0xE9723A1167d230a1259cd4511a73a89788208f3E",
            "token_template": "IbetStraightBond",
            "owner_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
            "company_name": "株式会社サンプル",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "name": "債券１",
            "symbol": "TESTBOND",
            "total_supply": 1000000,
            "face_value": 100,
            "interest_rate": 0,
            "interest_payment_date1": "",
            "interest_payment_date2": "",
            "interest_payment_date3": "",
            "interest_payment_date4": "",
            "interest_payment_date5": "",
            "interest_payment_date6": "",
            "interest_payment_date7": "",
            "interest_payment_date8": "",
            "interest_payment_date9": "",
            "interest_payment_date10": "",
            "interest_payment_date11": "",
            "interest_payment_date12": "",
            "redemption_date": "20190301",
            "redemption_amount": 0,
            "return_date": "20190301",
            "return_amount": "",
            "purpose": "プロジェクト資金として",
            "image_url": [
                {
                    "type": "small",
                    "url": ""
                },
                {
                    "type": "medium",
                    "url": "http://XXXX.com"
                },
                {
                    "type": "large",
                    "url": ""
                }
            ],
            "certification": [],
            "credit_card_availability": True,
            "bank_payment_availability": True
        }
    ]
}
```

* `id` : シーケンス
* `token_address` : トークンコントラクトのアドレス
* `token_template` : トークンテンプレート名（IbetStraightBond）
* `owner_address` : トークン発行体のEOA
* `company_name` : トークン発行体の会社名
* `rsa_publickey` : 発行会社にのみ通知する暗号化情報を登録するためのRSA公開鍵
* `name` : トークン名称
* `symbol` : トークン略称
* `total_supply` : トークン総発行数量
* `face_value` : 額面
* `interest_rate` : 金利[税引前]（%）
* `interest_payment_date1` : 利払日１
* `interest_payment_date2` : 利払日２
* `interest_payment_date3` : 利払日３
* `interest_payment_date4` : 利払日４
* `interest_payment_date5` : 利払日５
* `interest_payment_date6` : 利払日６
* `interest_payment_date7` : 利払日７
* `interest_payment_date8` : 利払日８
* `interest_payment_date9` : 利払日９
* `interest_payment_date10` : 利払日１０
* `interest_payment_date11` : 利払日１１
* `interest_payment_date12` : 利払日１２
* `redemption_date` : 償還日
* `redemption_amount` : 償還金額（額面当り）
* `return_date` : リターン実施日
* `return_amount` : リターン内容
* `purpose` : 発行目的
* `image_url` : 画像URL（`type` : 小/中/大, `url` : URL）
* `certification` : 第三者認定済アドレス
* `credit_card_availability` : クレジットカード決済可能フラグ
* `bank_payment_availability` : 銀行決済可能フラグ

#### Status: 400 Bad Request
* 入力値エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": {
            "cursor": [
                "field 'cursor' could not be coerced",
                "must be of integer type"
            ],
            "limit": [
                "field 'limit' could not be coerced",
                "must be of integer type"
            ]
        }
    }
}
```
* `description` : エラーになっている内容

## GET: /v1/Membership/Contracts
* 公開中の会員権トークンの一覧を返すAPI。
* 公開済み、かつ取扱ステータスが有効のものが一覧で返される。

### Sample
```sh
curl -X GET \
  'http://localhost:5000/v1/Membership/Contracts/?cursor=3&limit=1' \
  -H 'cache-control: no-cache'
```

### In
* `cursor` : 検索用のカーソルナンバー
* `limit` :　検索上限

#### validation
```py
{
        'cursor': {
            'type': 'integer',
            'coerce': int,
            'min':0,
            'required': False,
            'nullable': True,
        },
        'limit': {
            'type': 'integer',
            'coerce': int,
            'min':0,
            'required': False,
            'nullable': True,
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
            "id": 1,
            "token_address": "0x6F9a2C569cdeADb95472CC26EE0D9e73df4c186D",
            "token_template": "IbetMembership",
            "owner_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
            "company_name": "株式会社サンプル",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "name": "会員権１",
            "symbol": "TESTMEM",
            "total_supply": 1000000,
            "details": "会員権の詳細内容",
            "return_details": "リターンの詳細内容",
            "expiration_date": "20190331",
            "memo": "メモ欄",
            "transferable": true,
            "status": true,
            "initial_offering_status": false,
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
            ],
            "credit_card_availability": True,
            "bank_payment_availability": True
        }
    ]
}
```

* `id` : シーケンス
* `token_address` : トークンコントラクトのアドレス
* `token_template` : トークンテンプレート名（IbetMembership）
* `owner_address` : トークン発行体のEOA
* `company_name` : トークン発行体の会社名
* `rsa_publickey` : 発行会社にのみ通知する暗号化情報を登録するためのRSA公開鍵
* `name` : トークン名称
* `symbol` : トークン略称
* `total_supply` : トークン総発行数量
* `details` : 会員権詳細
* `return_details` : リターン詳細
* `expiration_date` : 有効期限
* `memo` : メモ欄
* `transferable` : 譲渡可能
* `status` : 有効/無効
* `initial_offering_status` : 新規募集ステータス
* `image_url` : 画像URL（`type` : 小/中/大, `url` : URL）
* `credit_card_availability` : クレジットカード決済可能フラグ
* `bank_payment_availability` : 銀行決済可能フラグ

#### Status: 400 Bad Request
* 入力値エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": {
            "cursor": [
                "field 'cursor' could not be coerced",
                "must be of integer type"
            ],
            "limit": [
                "field 'limit' could not be coerced",
                "must be of integer type"
            ]
        }
    }
}
```
* `description` : エラーになっている内容

## GET: /v1/Coupon/Contracts
* 公開中のクーポントークンの一覧を返すAPI。
* 公開済み、かつ取扱ステータスが有効のものが一覧で返される。

### Sample
```sh
curl -X GET \
  'http://localhost:5000/v1/Coupon/Contracts?cursor=3&limit=1' \
  -H 'cache-control: no-cache'
```

### In
* `cursor` : 検索用のカーソルナンバー
* `limit` :　検索上限

#### validation
```py
{
        'cursor': {
            'type': 'integer',
            'coerce': int,
            'min':0,
            'required': False,
            'nullable': True,
        },
        'limit': {
            'type': 'integer',
            'coerce': int,
            'min':0,
            'required': False,
            'nullable': True,
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
            "id": 2,
            "token_address": "0x9E5D93cE6A86a8254A7a1b67Eb03769D46359dDd",
            "token_template": "IbetCoupon",
            "owner_address": "0xc194a6A7EeCA0A57706993e4e4Ef4Cf1a3434e51",
            "company_name": "株式会社DEMO",
            "rsa_publickey": "-----BEGIN PUBLIC KEY-----\nMIIFIjANBgkqhkiG9w0BAQEFAAOCBQ8AMIIFCgKCBQEAtiBUQ2vdYvIqnCdUzKIC\np7jIYVtJy8KGniy6ktE0DTcYG70pFYkGDyI043meSB6Lkk0rNWaKBn3wyz4lx2oX\n3JySFyXR4vE4DNTEKS0htImO4RuK4M50v7LOfB8VphXzu9JkdVuN8LuMx6L6dhsd\nTN/aUvXULvjOy9AJekl24s44w4BgEfGj/uBYNAmiNmpM3lnIdJOg1T+4aEShHyVN\n98dv1DZ1Hh0YhMmqHqRGIzAQ6pKoly2xSVEmwBV4l2O3XEZ8ErVNgHdi6BRQrIBl\n+zQn5TysSGv5TIO1ahztUIygrzX7aEa+QnF1ROBBJ8yBW0VjjKI2Oh3wDT8ROaWb\ntB7gYQlMX9St/HJvGKaDKPDGurMFsEZeeD9Y4GWlFFkQplKIC3Kr4u6TIxcAZyG3\ntIz1IZomm/Lh9eiFiAbOMLYPdPCzh1A6uCRoJuqrNXYbE2egpLsKSkEe4VAcdaPo\nVuOXLpbDaew0cvXQR5IklHGGPPGVqQV1cmJWIqF5b1bzqziu2No+TLZceUd3N9Eh\nQIYVG4rbX2I/x2/WFeG5RHl9Zc/iSUomUqpnGY3ved61smb7uklF/7ueyj8TIm7O\ncJxhYjj+szXxV2RJyxLvSPzloQ4GDI9wd0zlya2CoYgAONJ7wm82b1LrLLhfpns2\ndSsN8htFX83p0dNn6f8ssKgA3rFbFFnBTQyFxlHO/An4qZflXtk1GsEc56g3mJFp\nrFANLpyum5mkHo9TbkL3K4mRGM1DGcLXWJwFUjDxS/OvjzDXw2dNiyrPeClvTpAb\npFfw/zqVd7ZrnTFg26bpUmM8flc6IRji49veOOMM7jMJN7mmu/pLd/Pg22oez23G\n6QsPDvqqXgjyg1NGo7natX6gyAYMpWZWOHj+Y2lffzcJYUo+wPFt/xNkAuCcDZem\nAiicfsGfniE67G1nfmwkykVwk9rTFCO8SnFei8wMpEAMYETYOS4ldavLfhY6mrF1\nItA5mlkMI84v3ROqPSp3s6F9oGYzPi5zMcgc67wIFGgaPb6i8+puui6BUbj83qOU\nKuKoQAGe9+NRnAkWSpbX07cX6XkPieTkBHEYfGaQTQOnsSs++PIk3kH5Arfjk0R5\nu1ZluzVdOXUn8D5WPfh9UFzqyXzo1HOIHxDkPejpPlNzO1w6qVQC+UiR/R2iug/U\n7StoLz476tQOwbfmnzUA6AbOKjRgN5laRoBac4BbGPJisGysOBruL7lgrw0XVtnh\nknChXfSYezxz/EtiGmO40HKAGudHDkz4gmPDkF4wlIyfDbQZOnNohz4zuOjr9Yi/\nJQVpqKxug2LXyJp38UaxL1LIT6ZyJSsaSrKAB21tsYAbksyPCVS6L6jkz8lsnlYg\nLj7lj6HQcbN8WO72+Z8Ddj/cPXJwEq4OTbtkPiPdcvSZjcBR9f3TmrQjDG0ROspt\nI/m4KhWfm7ed+eZKA1IqygFRyi6i0w6p+VbeBNgXqAiQI5GkDHqAiqv4OVyZoQB8\neunu5qM49r6bw6DJCqlg6lZDCptdKWtNBo9zgEegrJ/3oVI7x0kE7KQ4gPo5uY7j\nvBqGwjw0fIGPjrP/JKIQqGvm/ETwlfPwVbmCsvEHbqEY+6f84TnmolgjPMnbar6Q\nSDuvqVApY7yNCEue5X0pLRAd+287VBVVvsOsZVOSj02w4PGIlsg2Y33BbcpwESzr\n4McG/dPyTRFv9mYtFPpyV50CAwEAAQ==\n-----END PUBLIC KEY-----",
            "name": "クーポン１",
            "symbol": "TESTCP1",
            "total_supply": 1000000,
            "details": "クーポンの詳細内容",
            "return_details": "リターンの詳細内容",
            "memo": "メモ欄",
            "expiration_date": "20190331",
            "transferable": true,
            "status": true,
            "initial_offering_status": false,
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
            "credit_card_availability": True,
            "bank_payment_availability": True
        }
    ]
}
```

* `id` : シーケンス
* `token_address` : トークンコントラクトのアドレス
* `token_template` : トークンテンプレート名（IbetCoupon）
* `owner_address` : トークン発行体のEOA
* `company_name` : トークン発行体の会社名
* `rsa_publickey` : 発行会社にのみ通知する暗号化情報を登録するためのRSA公開鍵
* `name` : トークン名称
* `symbol` : トークン略称
* `total_supply` : トークン総発行数量
* `details` : クーポン詳細
* `return_details` : リターン詳細
* `memo` : メモ欄
* `expiration_date` : 有効期限
* `transferable` : 譲渡可能
* `status` : 有効/無効
* `initial_offering_status` : 新規募集ステータス
* `image_url` : 画像URL（`type` : 小/中/大, `url` : URL）
* `credit_card_availability` : クレジットカード決済可能フラグ
* `bank_payment_availability` : 銀行決済可能フラグ

#### Status: 400 Bad Request
* 入力値エラー時

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": {
            "cursor": [
                "field 'cursor' could not be coerced",
                "must be of integer type"
            ],
            "limit": [
                "field 'limit' could not be coerced",
                "must be of integer type"
            ]
        }
    }
}
```
* `description` : エラーになっている内容
