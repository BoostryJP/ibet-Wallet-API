#!/bin/bash
# shellcheck disable=SC1090
source ~/.bash_profile

cd /app/ibet-Wallet-API

if [ "$BOND_TOKEN_ENABLED" = 1 ]; then
  python async/processor_Notifications_Bond_Token.py &
  python async/processor_Notifications_Bond_Exchange.py &
fi

if [ "$SHARE_TOKEN_ENABLED" = 1 ]; then
  python async/processor_Notifications_Share_Token.py &
  python async/processor_Notifications_Share_Exchange.py &
fi

if [ "$MEMBERSHIP_TOKEN_ENABLED" = 1 ]; then
  python async/processor_Notifications_Membership_Exchange.py
fi

if [ "$COUPON_TOKEN_ENABLED" = 1 ]; then
  python async/processor_Notifications_Coupon_Token.py &
  python async/processor_Notifications_Coupon_Exchange.py &
fi
