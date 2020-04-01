#!/bin/bash
source ~/.bash_profile

cd /app/ibet-Wallet-API

# test
pytest -v --cov=app/api/ --cov-report=xml --cov-branch

status_code=$?

# カバレッジファイルの移動
mv coverage.xml cov/

if [ $status_code -ne 0 ]; then
  exit 1
fi