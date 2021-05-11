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

function start () {
    # check COMPANY_LIST_LOCK_MODE and COMPANY_LIST_URL
    if [[ "${APP_ENV:-}" != "local"  && "${COMPANY_LIST_LOCAL_MODE:-}" -ne 1  &&  -z "${COMPANY_LIST_URL:-}" ]]; then
      echo 'Please set APP_ENV "local" or COMPANY_LIST_LOCAL_MODE "1", if you use company list local mode,' >&2
      echo 'Please set COMPANY_LIST_URL company list url, if you do not use local mode.' >&2
      exit 1
    fi

    # COMPANY_LIST_URL
     resp=$(curl "${COMPANY_LIST_URL}" -o /dev/null -w '%{http_code}\n' -s)
     if [ "${resp}" -ne 200 ]; then
       echo "Please confirm COMPANY_LIST_URL, which response code is ${resp}"
       exit 1
     fi

    #source .venv/bin/activate
    python batch/processor_Block_Sync_Status.py &
    gunicorn -b 0.0.0.0:5000 --reload app.main:application --timeout 30 --workers=$WORKER_COUNT --max-requests 500 --max-requests-jitter 200 -k gevent
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
