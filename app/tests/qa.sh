#!/bin/bash
source ~/.bash_profile

cd /app/tmr-node

# test
pytest -v --cov=app/api/ --cov-report=xml --cov-branch

# カバレッジファイルの移動
mv coverage.xml cov/
