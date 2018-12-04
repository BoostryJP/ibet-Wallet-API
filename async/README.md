# バックプロセス起動方法

## processor_OrderAgree.py

- 各種環境変数は適宜環境に合わせて修正してください。
- テーブルの自動作成は行わないため、先にtmr-nodeを起動しておく必要があります。

```
$ export WEB3_HTTP_PROVIDER=http://localhost:8545
$ export DATABASE_URL=postgresql://ethuser:ethpass@localhost:5432/ethcache
$ export IBET_EXCHANGE_CONTRACT_ADDRESS=0x682e9123cb76b7842fb254c4c93dfce761e8faa4
$ python async/processor_OrderAgree.py
```

## processor_Notifications.py

環境変数は下記の通り

| 環境変数名                        | デフォルト値                                         | 説明                   | 例                                                   |
| --------------------------------- | ---------------------------------------------------- | ---------------------- | ---------------------------------------------------- |
| WEB3_HTTP_PROVIDER                | http://localhost:8545                                |                        | http://localhost:8545                                |
| DATABASE_URL                      | postgresql://ethuser:ethpass@localhost:5432/ethcache |                        | postgresql://ethuser:ethpass@localhost:5432/ethcache |
| IBET_SB_EXCHANGE_CONTRACT_ADDRESS |                                                      |                        | 0x682e9123cb76b7842fb254c4c93dfce761e8faa4           |
| WHITE_LIST_CONTRACT_ADDRESS       |                                                      |                        | 0x682e9123cb76b7842fb254c4c93dfce761e8faa4           |
| TOKEN_LIST_CONTRACT_ADDRESS       |                                                      |                        | 0x682e9123cb76b7842fb254c4c93dfce761e8faa4           |
| WORKER_COUNT                      | 8                                                    | イベント取得ワーカー数 | 10                                                   |
| SLEEP_INTERVAL                    | 3                                                    | イベント取得間隔       | 5                                                    |
