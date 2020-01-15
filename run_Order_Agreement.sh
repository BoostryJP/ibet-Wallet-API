#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/processor_OrderAgree.py &
python async/processor_Consume_coupon.py
