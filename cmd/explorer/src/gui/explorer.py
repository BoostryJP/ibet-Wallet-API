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
import sys

from textual.app import App, ReturnType
from textual.binding import Binding

from .screen.block import BlockScreen
from .screen.transaction import TransactionScreen

path = os.path.join(os.path.dirname(__file__), "../../../../")
sys.path.append(path)

from app.model.schema import ListTxDataQuery


class AppState:
    tx_query: ListTxDataQuery | None = None


class ExplorerApp(App):
    """A Textual app to explorer ibet-Network."""

    BINDINGS = [Binding("q", "quit", "Quit")]
    CSS_PATH = f"{os.path.dirname(os.path.abspath(__file__))}/explorer.css"
    SCREENS = {"transaction_screen": TransactionScreen}
    url: str
    state: AppState = AppState()

    async def run_async(
        self,
        *,
        url: str = "http://localhost:5000",
        headless: bool = False,
        size: tuple[int, int] | None = None,
        auto_pilot: None = None,
    ) -> ReturnType | None:
        self.url = url
        return await super().run_async(headless=headless, size=size, auto_pilot=auto_pilot)

    def on_mount(self):
        self.push_screen(BlockScreen(name="block_screen"))

    async def action_quit(self) -> None:
        self.exit()
