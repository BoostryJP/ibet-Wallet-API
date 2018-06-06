#!/bin/bash
source ~/.bash_profile

cd /app/tmr-node

# async
nohup python async/processor_OrderBook.py < /dev/null 2>&1 /dev/null &

#run server
./bin/run.sh start