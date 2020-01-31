#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/processor_Notifications_Bond_Token.py &
python async/processor_Notifications_Bond_Exchange.py &
python async/processor_Notifications_Coupon_Exchange.py &
python async/processor_Notifications_Membership_Exchange.py