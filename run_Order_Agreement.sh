#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/indexer_Transfer.py &
python async/indexer_OrderAgree.py &
python async/indexer_Consume_Coupon.py
