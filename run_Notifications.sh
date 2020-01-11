#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/processor_Notifications.py &

python async/processor_Notifications_bond.py