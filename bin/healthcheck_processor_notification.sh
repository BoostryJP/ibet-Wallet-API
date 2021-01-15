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

PROC_LIST="${PROC_LIST} async/processor_Block_Sync_Status.py"

if [ "${BOND_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Bond_Token.py"
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Bond_Exchange.py"
fi

if [ "${SHARE_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Share_Token.py"
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Share_Exchange.py"
fi

if [ "${MEMBERSHIP_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Membership_Exchange.py"
fi

if [ "${COUPON_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Coupon_Token.py"
  PROC_LIST="${PROC_LIST} async/processor_Notifications_Coupon_Exchange.py"
fi

for i in ${PROC_LIST}; do
  # shellcheck disable=SC2009
  ps -ef | grep -v grep | grep "$i"
  if [ $? -ne 0 ]; then
    exit 1
  fi
done

