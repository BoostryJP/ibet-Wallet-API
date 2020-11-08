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
# software distributed under the License is distributed onan "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

function start () {
    #source .venv/bin/activate
    gunicorn -b 0.0.0.0:5000 --reload app.main:application --timeout 30 --workers=$WORKER_COUNT --max-requests 500 --max-requests-jitter 200 -k gevent
}

function stop () {
    ps -ef | grep gunicorn | awk '{print $2}' | xargs kill -9
}


case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
    echo "Usage: run.sh {start|stop}"
    exit 1
esac
