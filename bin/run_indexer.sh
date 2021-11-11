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

# shellcheck disable=SC1090
source ~/.bash_profile

cd /app/ibet-Wallet-API

if [[ "${APP_ENV:-}" != "local" && "${COMPANY_LIST_LOCAL_MODE:-}" -ne 1 ]]; then
  # check COMPANY_LIST_LOCAL_MODE and COMPANY_LIST_URL
  if [ -z "${COMPANY_LIST_URL:-}" ]; then
    echo -n '[ERROR] Please set APP_ENV "local" or COMPANY_LIST_LOCAL_MODE "1", if you use company list local mode, ' >&2
    echo 'please set COMPANY_LIST_URL company list url, if you do not use local mode.' >&2
    exit 1
  fi
  # check COMPANY_LIST_URL available
  resp=$(curl "${COMPANY_LIST_URL}" -o /dev/null -w '%{http_code}\n' -s)
  if [ "${resp}" -ne 200 ]; then
    echo -n "[WARNING] Could not access to COMPANY_LIST_URL, " >&2
    echo "please confirm COMPANY_LIST_URL, which response code is ${resp}" >&2
  fi
  python batch/indexer_CompanyList.py &
fi

python batch/indexer_Transfer.py &

if [ $SHARE_TOKEN_ENABLED = 1 ]; then
  python batch/indexer_Position_Share.py &
  python batch/indexer_TransferApproval.py &
fi

if [ $BOND_TOKEN_ENABLED = 1 ]; then
  python batch/indexer_Position_Bond.py &
fi

if [ $MEMBERSHIP_TOKEN_ENABLED = 1 ]; then
  python batch/indexer_Position_Membership.py &
fi

if [ $COUPON_TOKEN_ENABLED = 1 ]; then
  python batch/indexer_Consume_Coupon.py &
  python batch/indexer_Position_Coupon.py &
fi

if [ -n "$IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS" -o \
  -n "$IBET_SB_EXCHANGE_CONTRACT_ADDRESS" -o \
  -n "$IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS" -o \
  -n "$IBET_CP_EXCHANGE_CONTRACT_ADDRESS" ]; then
  python batch/indexer_DEX.py &
fi

tail -f /dev/null
