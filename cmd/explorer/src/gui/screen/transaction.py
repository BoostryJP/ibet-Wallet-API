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

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import DataTable, Footer, Label

import connector
from gui.consts import ID
from gui.screen.base import TuiScreen
from gui.widget.block_list_table import BlockListTable
from gui.widget.tx_detail_view import TxDetailView
from gui.widget.tx_list_table import TxListTable
from gui.widget.tx_list_view import TxListView

path = os.path.join(os.path.dirname(__file__), "../../../../../")
sys.path.append(path)

from app.model.schema.bc_explorer import TxDataDetail


class TransactionScreen(TuiScreen):
    BINDINGS = [Binding("q", "quit", "Close", priority=True)]

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Horizontal(
                    Label(Text.from_markup(" [bold]ibet-Wallet-API BC Explorer[/bold]")),
                    Label(" | "),
                    Label(f"Selected block: -", id=ID.SELECTED_BLOCK_NUMBER),
                    id="header",
                ),
                Horizontal(TxListView(classes="column"), TxDetailView(classes="column")),
                classes="column",
            )
        )
        yield Footer()

    async def on_mount(self) -> None:
        self.query(TxListTable)[0].focus()

    def action_quit(self):
        self.tui.pop_screen()
        self.tui.query(BlockListTable)[0].can_focus = True
        self.tui.query(BlockListTable)[0].focus()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_row = self.query_one(TxListTable).data.get(event.cursor_row)
        if selected_row is None:
            return

        tx_hash = selected_row[0]
        async with TCPConnector(limit=1) as tcp_connector:
            async with ClientSession(connector=tcp_connector, timeout=ClientTimeout(10)) as session:
                tx_detail: TxDataDetail = await connector.get_tx_data(
                    session,
                    self.tui.url,
                    tx_hash,
                )
                self.query_one(TxDetailView).tx_detail = tx_detail

    async def on_screen_suspend(self):
        self.query_one(TxListTable).update_rows([])

    async def on_screen_resume(self):
        if self.tui.state.tx_query is not None:
            async with TCPConnector(limit=1) as tcp_connector:
                async with ClientSession(connector=tcp_connector, timeout=ClientTimeout(10)) as session:
                    tx_list = await connector.list_tx_data(
                        session=session, url=self.tui.url, query=self.tui.state.tx_query
                    )
                    self.query_one(TxListTable).update_rows(tx_list.tx_data)
                    self.query_one(f"#{ID.SELECTED_BLOCK_NUMBER}", Label).update(
                        f"Selected block: {self.tui.state.tx_query.block_number}"
                    )
