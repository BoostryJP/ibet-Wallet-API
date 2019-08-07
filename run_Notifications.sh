#!/bin/bash
source ~/.bash_profile

cd /app/tmr-node

python async/processor_Notifications.py < /dev/null 2>&1 /dev/null &

python async/processor_Notifications_mrf.py