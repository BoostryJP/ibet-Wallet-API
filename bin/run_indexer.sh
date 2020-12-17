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
# software distributed under the License is distributed onan "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# shellcheck disable=SC1090
source ~/.bash_profile

cd /app/ibet-Wallet-API

python async/indexer_DEX.py &

python async/indexer_Transfer.py &

if [ $SHARE_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Position_Share.py &
fi

if [ $BOND_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Position_Bond.py &
fi

if [ $MEMBERSHIP_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Position_Membership.py &
fi

if [ $COUPON_TOKEN_ENABLED = 1 ]; then
  python async/indexer_Consume_Coupon.py &
  python async/indexer_Position_Coupon.py &
fi

tail -f /dev/null
