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

if [[ "${APP_ENV:-}" != "local" && "${COMPANY_LIST_LOCAL_MODE:-}" -ne 1 ]]; then
  PROC_LIST="${PROC_LIST} batch/indexer_CompanyList.py"
fi

PROC_LIST="${PROC_LIST} batch/indexer_Transfer.py"
PROC_LIST="${PROC_LIST} batch/indexer_Token_Holders.py"

if [ "${SHARE_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} batch/indexer_Position_Share.py"
  PROC_LIST="${PROC_LIST} batch/indexer_TransferApproval.py"
fi

if [ "${BOND_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} batch/indexer_Position_Bond.py"
fi

if [ "${MEMBERSHIP_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} batch/indexer_Position_Membership.py"
fi

if [ "${COUPON_TOKEN_ENABLED}" = 1 ]; then
  PROC_LIST="${PROC_LIST} batch/indexer_Consume_Coupon.py"
  PROC_LIST="${PROC_LIST} batch/indexer_Position_Coupon.py"
fi

if [ -n "$IBET_SHARE_EXCHANGE_CONTRACT_ADDRESS" -o \
  -n "$IBET_SB_EXCHANGE_CONTRACT_ADDRESS" -o \
  -n "$IBET_MEMBERSHIP_EXCHANGE_CONTRACT_ADDRESS" -o \
  -n "$IBET_CP_EXCHANGE_CONTRACT_ADDRESS" ]; then
  PROC_LIST="${PROC_LIST} batch/indexer_DEX.py"
fi

if [ -z $TOKEN_CACHE ] || [ $TOKEN_CACHE -ne 0 ]; then
  PROC_LIST="${PROC_LIST} batch/indexer_Token_Detail.py"
  PROC_LIST="${PROC_LIST} batch/indexer_Token_Detail_ShortTerm.py"
fi

for i in ${PROC_LIST}; do
  # shellcheck disable=SC2009
  ps -ef | grep -v grep | grep "$i"
  if [ $? -ne 0 ]; then
    exit 1
  fi
done
