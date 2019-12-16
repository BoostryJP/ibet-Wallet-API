#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/processor_Notifications.py < /dev/null 2>&1 /dev/null &

python async/processor_Notifications_bond.py