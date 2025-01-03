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

import logging
import sys
from typing import cast

from app import config
from logger import SystemLogger


def get_logger(process_name: str = None):
    logging.setLoggerClass(SystemLogger)
    LOG = cast(SystemLogger, logging.getLogger("ibet_wallet_batch"))
    LOG.propagate = False
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        config.INFO_LOG_FORMAT.format(f"[{process_name}]"), config.LOG_TIMESTAMP_FORMAT
    )
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

    return LOG
