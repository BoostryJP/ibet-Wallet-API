# ドキュメント作成方法

## python実行環境の作成
* ローカル開発環境、テスト環境と同様にpython実行環境を作成する。

## ライブラリのインストール
* ドキュメントビルダーとしてSphinxを利用する。
* ドキュメント作成に必要なライブラリをインストールする。

```sh
$ cd ./ibet-Wallet-API/doc/
$ pip install -r requirements.txt
```

## ドキュメントの作成
* `ibet-Wallet-API/doc/source`の下にmarkdown形式のドキュメントを作成する。
* `index.rst`に作成したmarkdownファイルのリンクを記述するとtoctreeが作成される。

## ビルド（HTMLファイル作成）
```sh
$ make html
```
* 上記コマンドを実行すると、read the docsテーマのHTMLファイルが作成される。
* 作成されたファイルは（htmlファイル、JSファイルなど）、`ibet-Wallet-API/doc/build`の下に全て格納される。
