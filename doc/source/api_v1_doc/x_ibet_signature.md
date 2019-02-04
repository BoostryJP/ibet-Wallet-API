# X-ibet-Signature

## Abstract

更新系APIに対して、改ざん防止及び、認証機能を付与するための仕様。
更新系APIとしては以下のようなものが想定される。
- 通知の既読・重要フラグの更新
- プッシュ通知のための端末情報登録

本仕様では、下記の担保を目的とする。
- リクエストの下記項目が改ざんされていないこと（署名機能）
  - HTTPメソッド
  - path(queryString含む)
  - requestBody
- リクエストを送信したユーザーのEthereumアドレスが特定できること（認証機能）

## Specification

### 定義

#### keccak256関数

文字列をsha3でハッシュ化したものを16進数文字列でエンコードしたもの。
（先頭に0xをつける）

#### CanonicalRequest

```
CanonicalRequest =
  HTTPMethod + '\n' +
  CanonicalRequestPath + '\n' +
  CanonicalQueryString + '\n' +
  keccak256(RequestBody)
```

- HTTPMethod: `GET`、`POST`などの文字列
- CanonicalRequestPath: URIのPath部分（例：`/v1/UpdateNotification`）
- CanonicalQueryString: クエリ文字列をkeyでソートしたもの（例：`?amount=123&card=hoge`）
- *注：CanonicalQueryStringがない場合、空文字扱いとなります*
- *注：`keccak256(RequestBody)`はRequestBodyが空の場合、`keccak256("{}")`を用います*

### 署名・認証手続き概要

#### Client Side（署名）

1. 送信するリクエストの情報から **CanonicalRequest** を生成する。
    - 参考：keccak256の生成方法 https://web3js.readthedocs.io/en/1.0/web3-utils.html?highlight=keccak256#sha3
1. アカウントの秘密鍵を用いて、 **CanonicalRequest** に署名を行う。
    - 参考：http://web3js.readthedocs.io/en/1.0/web3-eth-accounts.html#sign
    - 参考：https://gist.github.com/t-tojima/b1ebbdf427fa3cd749e87be625c3de9e
1. 生成された署名(signature)を、 `X-ibet-Signature`ヘッダに書き込み、リクエストを送信する。

#### Server Side（署名検証）

1. 受信したリクエストの情報から **CanonicalRequest** を生成する。
1. `X-ibet-Signature`ヘッダの情報と **CanonicalRequest** から署名検証を行う。
    - 参考：https://gist.github.com/t-tojima/b1ebbdf427fa3cd749e87be625c3de9e
1. 署名検証メソッドからアカウントのアドレスを取得する。
