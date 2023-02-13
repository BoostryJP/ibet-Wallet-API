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
from enum import Enum

UP = "\u2191"
DOWN = "\u2193"
LEFT = "\u2190"
RIGHT = "\u2192"
RIGHT_TRIANGLE = "\u25B6"
BIG_RIGHT_TRIANGLE = "\uE0B0"
DOWN_TRIANGLE = "\u25BC"

THINKING_FACE = ":thinking_face:"
FIRE = ":fire:"
INFO = "[blue]:information:[/]"


class ID(str, Enum):
    BLOCK_LIST_FILTER = "block_list_filter"
    BLOCK_LIST_LOADED_TIME = "block_list_loaded_time"
    BLOCK_LIST_LOADING = "block_list_loading"
    BLOCK_LIST_HEADER = "block_list_header"

    CONNECTED = "connected"
    CURRENT_BLOCK_NUMBER = "current_block_number"
    IS_SYNCED = "is_synced"
    TX_COUNT_5M = "tx_count_5m"
    HEADER = "header"

    SELECTED_BLOCK_NUMBER = "selected_block_number"
