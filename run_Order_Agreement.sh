#!/bin/bash
# shellcheck disable=SC1090
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/indexer_Transfer.py &
python async/indexer_OrderAgree.py

if [ $COUPON_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Consume_Coupon.py
fi
