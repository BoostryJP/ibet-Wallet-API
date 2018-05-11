# バックプロセス起動方法

## processor_OrderBook.py

- 各種環境変数は適宜環境に合わせて修正してください。
- テーブルの自動作成は行わないため、先にtmr-nodeを起動しておく必要があります。

```
$ export WEB3_HTTP_PROVIDER=http://localhost:8545
$ export DATABASE_UR+=postgresql://ethuser:ethpass@localhost:5432/ethcache
$ export IBET_EXCHANGE_CONTRACT_ADDRESS=0x682e9123cb76b7842fb254c4c93dfce761e8faa4
$ python async/processor_OrderBook.py
```
