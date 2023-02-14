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
from pydantic import BaseModel
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button

from gui.widget.base import TuiWidget


class MenuInstruction(BaseModel):
    block_number: int
    block_hash: str
    selected_row: int


class Menu(TuiWidget):
    BINDINGS = [
        Binding("tab,down,ctrl+n", "focus_next", "Focus Next", show=False),
        Binding("shift+tab,up,ctrl+p", "focus_previous", "Focus Previous", show=False),
        Binding("ctrl+r", "", "", show=False),
        Binding("t", "click('show_transactions')", "Show Transactions"),
        Binding("c,q", "click('cancel')", "Cancel", key_display="Q, C"),
    ]
    ix: MenuInstruction | None = None

    def compose(self) -> ComposeResult:
        yield Button(Text.from_markup("\[t] Show Transactions :package:"), id="show_transactions", classes="menubutton")
        yield Button("\[c] Cancel", id="cancel", classes="menubutton")

    def show(self, ix: MenuInstruction):
        self.ix = ix
        self.add_class("visible")
        self.query_one("#show_transactions", Button).focus()

    def hide(self) -> MenuInstruction | None:
        self.remove_class("visible")
        return self.ix

    def action_click(self, _id: str):
        self.query_one(f"#{_id}", Button).press()
