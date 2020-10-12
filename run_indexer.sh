#!/bin/bash
# shellcheck disable=SC1090
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/indexer_Transfer.py &
python async/indexer_OrderAgree.py &

if [ $SHARE_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Position_Share.py &
fi

if [ $BOND_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Position_Bond.py &
fi

if [ $MEMBERSHIP_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Position_Membership.py &
fi

if [ $COUPON_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Consume_Coupon.py &
  python async/indexer_Position_Coupon.py &
fi

tail -f /dev/null
