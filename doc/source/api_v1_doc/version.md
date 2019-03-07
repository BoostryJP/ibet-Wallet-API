# アプリケーションバージョン

## GET: /v1/RequiredVersion
* 強制アップデートに必要なバージョン情報を取得するAPI

### Sample
```sh
curl -X GET　\
    'http://localhost:5000/v1/RequiredVersion?platform=ios' \
    -H 'cache-control: no-cache'
```

* `platform` : スマートフォンOSの情報（`ios`または`android`のみ許可）

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
        "required_version": "1.0.0",
        "force": True,
        "update_url": "https://play.google.com/store/apps/details?id=jp.co.nomura.nomurastock"
    }
}
```

* `required_version` : 動作保証しているアプリケーションバージョン（iOS/Androidで異なる）
* `force` : 強制アップデートの要否（`True` or `False`）
* `update_url` : アップデートさせるアプリケーションのダウンロードURL
