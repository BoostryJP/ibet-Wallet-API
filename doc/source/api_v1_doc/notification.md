# 通知一覧

## GET: /v1/NotificationCount/
* 通知の未読件数を取得するAPI。

### Sample
```sh
curl -X GET \
  http://localhost:5000/v1/NotificationCount \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
なし

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
        "unread_counts": 0
    }
}
```
* `unread_counts` : 未読件数

#### Status: 400 Bad Request
* X-ibet-Signatureの署名誤り時。

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "failed to recover hash"
    }
}
```


## GET: /v1/Notifications/
* 通知内容を返却するAPI。

### Sample
```sh
curl -X GET \
  http://localhost:5000/v1/Notifications \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
* `cursor` : 検索用のカーソルナンバー（未設定の場合：0）
* `limit` : 取得件数（未設定の場合：10）
* `sort` : ソート順（`priority`: 優先度の高い順＞通知の新しい順、未設定の場合: 通知の新しい順）
* `status` : 返却対象の通知ステータス（`flagged`: 保存済、`deleted`: 削除済、未設定の場合: 未削除の明細を取得）

#### validation
```py
{
    "cursor": {
        "type": "integer",
        "coerce": int,
        "min":0,
        "required": False,
        "nullable": True,
    },
    "limit": {
        "type": "integer",
        "coerce": int,
        "min":0,
        "required": False,
        "nullable": True,
    },
    "sort": {
        "type": "string",
        "required": False,
        "nullable": True,
    },
    "status": {
        "type": "string",
        "required": False,
        "nullable": True,
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
    "data": {
        "notifications": [
          {
              "notification_type": "SampleNotification1",
              "id": "0x00000021034300000000000000",
              "sort_id": 1,
              "priority": 1,
              "block_timestamp": "2017/06/10 10:00:00",
              "is_read": true,
              "is_flagged": false,
              "is_deleted": false,
              "deleted_at": null,
              "args": {
                  "hoge": "fuga"
              },
              "metainfo": {
                  "aaa": "bbb"
              }
          },
          {
              "notification_type": "SampleNotification3",
              "id": "0x00000011034000000000000000",
              "sort_id": 2,
              "priority": 2,
              "block_timestamp": "2017/04/10 10:00:00",
              "is_read": false,
              "is_flagged": true,
              "is_deleted": false,
              "deleted_at": null,
              "args": {
                  "hoge": "fuga"
              },
              "metainfo": {
              }
          }
        ]
    }
}
```
* `notification_type` : 通知タイプ
  * `PaymentAccountRegister` : 決済用口座登録
  * `PaymentAccountApprove` : 決済用口座承認
  * `PaymentAccountWarn` : 決済用口座警告
  * `PaymentAccountUnapprove` : 決済用口座非承認
  * `PaymentAccountBan` : 決済用口座アカウント停止
  * `NewOrder` : 新規注文
  * `CancelOrder` : 注文取消
  * `BuyAgreement` : 買約定
  * `SellAgreement` : 売約定
  * `BuySettlementOK` : 決済承認（買）
  * `SellSettlementOK` : 決済承認（売）
  * `SettlementNG` : 決済非承認（買）
  * `SellSettlementNG` : 決済非承認（売）
  * `MembershipTransfer` : 会員権割当・譲渡
  * `CouponTransfer` : クーポン割当・譲渡
* `id` : 通知ID
  * 0x | `<blockNumber>` | `<transactionIndex>` | `<logIndex>` | `<optionType>`
  * ( | は文字列連結 )
  * `<blockNumber>`: blockNumberをhexstringで表現したもの。12桁
  * `<transactionIndex>`: transactionIndex（block内でのトランザクションの採番）をhexstringで表現したもの。6桁
  * `<logIndex>`: logIndex（transaction内でのログの採番）をhexstringで表現したもの。6桁
  * `<optionType>`: blockNumber, transactionIndex, logIndexが等しいが、通知としては複数にしたい場合に使用する識別子。2桁(デフォルトは00)
* `sort_id` : ソートID
* `priority` : 通知優先度（高:1, 中:2, 低:3）
* `block_timestamp` : ブロックタイムスタンプ。通知登録日時と同義。
* `is_read` : 既読/未読
* `is_flagged` : 保存済/未保存
* `is_deleted` : 削除済/未削除
* `deleted_at` : 削除日時
* `args` : 通知イベントの内容（各種コントラクトから発生するイベント情報のそのまま）
* `metainfo` : 通知のメタデータ

#### Status: 400 Bad Request
* X-ibet-Signatureの署名誤り時。

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "failed to recover hash"
    }
}
```

#### Status: 400 Bad Request
* 入力値エラー。

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": ""
    }
}
```
* `description` : エラー内容


## POST: /v1/Notifications/
* 通知内容を更新するAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Notifications \
  -H 'Content-Type: application/json' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache' \
  -d '{
    "id": "0x00000021034000000000000000",
    "is_read": true,
    "is_flagged": true,
    "is_deleted": true
}'
```
* `X-ibet-Signature` : クライアント認証、リクエスト認可に用いる署名情報。 [参考：X-ibet-Signature](x_ibet_signature.md)

### In
```json
{
    "id": "0x00000021034000000000000000",
    "is_read": true,
    "is_flagged": true,
    "is_deleted": true
}
```
* `id` : 通知ID
* `is_read` : 既読/未読　※更新を行いたい状態を指定
* `is_flagged` : 保存済/未保存　※更新を行いたい状態を指定
* `is_deleted` : 削除済/未削除　※更新を行いたい状態を指定

#### validation
```py
{
    "id": {
        "type": "string",
        "required": True,
        "empty": False,
    },
    "is_read": {
        "type": "boolean",
        "required": False,
    },
    "is_flagged": {
        "type": "boolean",
        "required": False,
    },
    "is_deleted": {
        "type": "boolean",
        "required": False,
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
    "data": {
        "notifications": [
          {
              "notification_type": "SampleNotification1",
              "id": "0x00000021034300000000000000",
              "sort_id": 1,
              "priority": 1,
              "block_timestamp": "2017/06/10 10:00:00",
              "is_read": true,
              "is_flagged": false,
              "is_deleted": false,
              "deleted_at": null,
              "args": {
                  "hoge": "fuga"
              },
              "metainfo": {
                  "aaa": "bbb"
              }
          },
          {
              "notification_type": "SampleNotification3",
              "id": "0x00000011034000000000000000",
              "sort_id": 2,
              "priority": 2,
              "block_timestamp": "2017/04/10 10:00:00",
              "is_read": false,
              "is_flagged": true,
              "is_deleted": false,
              "deleted_at": null,
              "args": {
                  "hoge": "fuga"
              },
              "metainfo": {
              }
          }
        ]
    }
}
```

#### Status: 400 Bad Request
* X-ibet-Signatureの署名誤り時。

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "failed to recover hash"
    }
}
```

#### Status: 400 Bad Request
* 入力値エラー。

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": ""
    }
}
```
* `description` : エラー内容

#### Status: 404 Not Found
* `id`で指定したデータが存在しない場合。

```json
{
    "meta": {
        "code": 30,
        "message": "Data Not Exists",
        "description": "notification not found"
    }
}
```


## POST: /v1/Notifications/Read/
* 通知の全件既読を行うAPI。

### Sample
```sh
curl -X POST \
  http://localhost:5000/v1/Notifications/Read \
  -H 'Content-Type: application/json' \
  -H 'X-ibet-Signature: 0x99be687c42c1f2e2a6178d4cab4c07203ed8e14f37c97b7af85e293454d0705c3670cb699353bcb205a0499fae2d92cf10cef79699d76aa587d0ba5e1a8349e61b' \
  -H 'cache-control: no-cache' \
  -d '{
  "is_read":true
}'
```

### In
```json
{
  "is_read":true
}
```
* `is_read` : 既読/未読　※更新を行いたい状態を指定

#### validation
```py
{
    "is_read": {
        "type": "boolean",
        "required": True,
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
    "data": null
}
```

#### Status: 400 Bad Request
* X-ibet-Signatureの署名誤り時。

```json
{
    "meta": {
        "code": 88,
        "message": "Invalid Parameter",
        "description": "failed to recover hash"
    }
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
