#!/bin/bash

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

PROC_LIST="${PROC_LIST}"

if [ "${TOKEN_NOTIFICATION_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} batch/processor_Notifications_Token.py"
fi

if [ "${EXCHANGE_NOTIFICATION_ENABLED}" = 1 ]; then
  if [ "${MEMBERSHIP_TOKEN_ENABLED}" = 1 ]; then
    if [ ! -z "${IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS}" ]; then
      PROC_LIST="${PROC_LIST} batch/processor_Notifications_Membership_Exchange.py"
    fi
  fi

  if [ "${COUPON_TOKEN_ENABLED}" = 1 ]; then
    if [ ! -z "${IBET_COUPON_EXCHANGE_CONTRACT_ADDRESS}" ]; then
      PROC_LIST="${PROC_LIST} batch/processor_Notifications_Coupon_Exchange.py"
    fi
  fi
fi

if [ ! -z "${SMTP_SERVER_HOST}" ]; then
  PROC_LIST="${PROC_LIST} batch/processor_Send_Mail.py"
fi

PROC_LIST="${PROC_LIST} batch/processor_Block_Sync_Status.py"

for i in ${PROC_LIST}; do
  # shellcheck disable=SC2009
  ps -ef | grep -v grep | grep "$i"
  if [ $? -ne 0 ]; then
    exit 1
  fi
done
