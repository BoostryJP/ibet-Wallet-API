#!/bin/bash
source ~/.bash_profile
cd /app/ibet-Wallet-API
cd ./migrations

python manage.py upgrade
