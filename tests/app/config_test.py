"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
import os
from importlib import reload
from unittest import mock


class TestTransactionWaitPollLatency:
    # テスト対象: TRANSACTION_WAIT_POLL_LATENCY

    def teardown(self):
        from app import config

        reload(config)

    # ＜正常系1＞: デフォルト値
    def test_normal_1(self):
        from app import config

        # Reload imported module to initialize with mocked env value
        reload(config)

        assert config.TRANSACTION_WAIT_POLL_LATENCY == 0.5

    # ＜正常系2＞: 小数値
    def test_normal_2(self):
        with mock.patch.dict(
            os.environ, {"TRANSACTION_WAIT_POLL_LATENCY": "0.1"}, clear=False
        ):
            from app import config

            # Reload imported module to initialize with mocked env value
            reload(config)

            assert config.TRANSACTION_WAIT_POLL_LATENCY == 0.1

    # ＜正常系3＞: 整数値
    def test_normal_3(self):
        with mock.patch.dict(
            os.environ, {"TRANSACTION_WAIT_POLL_LATENCY": "1.0"}, clear=False
        ):
            from app import config

            # Reload imported module to initialize with mocked env value
            reload(config)

            assert config.TRANSACTION_WAIT_POLL_LATENCY == 1
