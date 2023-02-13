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
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Label

from ..consts import ID
from .base import TuiWidget
from .block_list_table import BlockListTable


class BlockListView(TuiWidget):
    BINDINGS = [
        Binding("t", "filter", "Toggle Only Blocks Including Tx"),
    ]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Label("  "),
            Label("Only Blocks Including Tx: ▫️", id=ID.BLOCK_LIST_FILTER),
            Label("      "),
            Label("Loaded Time: ", id=ID.BLOCK_LIST_LOADED_TIME),
            Label("      "),
            Label("", id=ID.BLOCK_LIST_LOADING),
            id="block_list_description",
        )
        yield BlockListTable(name="blocks", complete_refresh=True)

    async def action_filter(self):
        toggle = self.query_one(BlockListTable).toggle_filter()
        match toggle:
            case True:
                self.query_one(f"#{ID.BLOCK_LIST_FILTER}").update(f"Only Blocks Including Tx: ☑️")
            case False:
                self.query_one(f"#{ID.BLOCK_LIST_FILTER}").update(f"Only Blocks Including Tx: ▫️")
