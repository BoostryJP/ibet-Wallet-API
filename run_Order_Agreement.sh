#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/processor_OrderAgree.py < /dev/null 2>&1 /dev/null &
python async/processor_OrderAgree_Swap.py
