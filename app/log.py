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

from app import config


logging.basicConfig(level=config.LOG_LEVEL)
LOG = logging.getLogger('ibet_wallet_app')
LOG.propagate = False

if config.APP_ENV == 'live':
    stream_handler = logging.StreamHandler(open(config.APP_LOGFILE, "a"))
    formatter = logging.Formatter(
        config.INFO_LOG_FORMAT.format("[APP-LOG]"),
        config.LOG_TIMESTAMP_FORMAT
    )
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

if config.APP_ENV == 'dev' or config.APP_ENV == 'local':
    stream_handler = logging.StreamHandler(open(config.APP_LOGFILE, "a"))
    formatter = logging.Formatter(
        config.DEBUG_LOG_FORMAT.format("[APP-LOG]"),
        config.LOG_TIMESTAMP_FORMAT
    )
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)


def get_logger():
    return LOG
