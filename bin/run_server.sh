#!/usr/bin/env bash

# Copyright BOOSTRY Co., Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

source ~/.bash_profile

cd /app/ibet-Wallet-API

if [[ "${APP_ENV:-}" == "local" || "${COMPANY_LIST_LOCAL_MODE:-}" -eq 1 ]]; then
  # check company_list.json is default one
  content_length="$(wc -c data/company_list.json | awk '{print $1}')"
  if [ "${content_length}" = 2 ]; then
    echo '[WARNING] company_list.json is empty. Please mount company_list.json if you use company list local mode.' >&2
  fi
fi

function start () {

    #source .venv/bin/activate
    python batch/processor_Block_Sync_Status.py &
    gunicorn -b 0.0.0.0:5000 app.main:app --timeout 30 --workers=$WORKER_COUNT --max-requests 500 --max-requests-jitter 200 --limit-request-line 0 -k server.AppUvicornWorker
}

function stop () {
    ps -ef | grep gunicorn | awk '{print $2}' | xargs kill -9
    ps -ef | grep "batch/processor_Block_Sync_Status.py" | awk '{print $2}' | xargs kill -9
}


case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
    echo "Usage: run_server.sh {start|stop}"
    exit 1
esac
