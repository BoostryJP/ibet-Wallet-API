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
import asyncio
import os
import sys
import time
from asyncio import Event, Lock
from datetime import datetime
from typing import Coroutine, Optional

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import Reactive
from textual.widgets import Button, DataTable, Footer, Label, Static

import connector
from gui.consts import ID
from gui.error import Error
from gui.screen.base import TuiScreen
from gui.widget.block_detail_view import BlockDetailView
from gui.widget.block_list_table import BlockListTable
from gui.widget.block_list_view import BlockListView
from gui.widget.menu import Menu, MenuInstruction

path = os.path.join(os.path.dirname(__file__), "../../../../../")
sys.path.append(path)

from app.model.schema import (
    BlockDataDetail,
    BlockDataListResponse,
    GetBlockSyncStatusResponse,
    ListBlockDataQuery,
    ListTxDataQuery,
)
from app.model.schema.base import SortOrder


class BlockScreen(TuiScreen):
    BINDINGS = [Binding("q", "quit", "Quit"), Binding("ctrl+r", "reload_block", "Reload block data")]
    dark = Reactive(True)
    background_lock: Optional[Event] = None
    current_block_number = Reactive(0)
    lock_reload_block = Reactive(Lock())
    __block_detail: Optional[BlockDataDetail] = None

    def __init__(self, name: str | None = None, id: str | None = None, classes: str | None = None):
        super().__init__(name=name, id=id, classes=classes)
        self.base_url = self.tui.url
        self.refresh_rate = 3.0
        self.block_detail_header_widget = BlockDetailView(classes="column")

    def compose(self) -> ComposeResult:
        yield Horizontal(
            Vertical(
                Horizontal(
                    Label(Text.from_markup(" [bold]ibet-Wallet-API BC Explorer[/bold]")),
                    Label(" | "),
                    Label("Fetching current block...", id=ID.BLOCK_CURRENT_BLOCK_NUMBER),
                    Label(" | "),
                    Label("Fetching current status...", id=ID.BLOCK_IS_SYNCED),
                    Label(" | "),
                    Label("Fetching transaction count...", id=ID.BLOCK_TX_COUNT_5M),
                    id=ID.BLOCK_SCREEN_HEADER,
                ),
                Horizontal(BlockListView(classes="column"), self.block_detail_header_widget),
                classes="column",
            )
        )
        yield Footer()
        yield Menu(id=ID.MENU)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        event.prevent_default()
        match event.button.id:
            case "cancel":
                self.query_one(Menu).hide()
                self.query(BlockListTable)[0].can_focus = True
                self.query_one(BlockListTable).focus()
            case "show_transactions":
                ix = self.query_one(Menu).hide()
                get_query = ListTxDataQuery()
                get_query.block_number = ix.block_number
                self.tui.state.tx_query = get_query
                await self.app.push_screen("transaction_screen")
        event.stop()

    async def on_mount(self) -> None:
        self.query_one(Menu).hide()
        self.query(BlockListTable)[0].focus()
        asyncio.create_task(self.background_execution(self.refresh_rate))

    async def background_execution(self, refresh_rate: float):
        self.background_lock = Event()
        block_number = None
        async with TCPConnector(limit=1, keepalive_timeout=60) as tcp_connector:
            async with ClientSession(connector=tcp_connector, timeout=ClientTimeout(30)) as session:
                while self.is_running:
                    start = time.time()
                    tasks: list[Coroutine] = [connector.get_node_info(session, self.base_url)]
                    if block_number is not None:
                        if self.current_block_number == 0:
                            self.current_block_number = block_number
                            asyncio.create_task(self.action_reload_block())
                        else:
                            self.current_block_number = block_number
                        tasks.append(
                            connector.list_block_data(
                                session,
                                self.base_url,
                                ListBlockDataQuery(
                                    to_block_number=block_number,
                                    from_block_number=max(block_number - 100, 0),
                                    sort_order=SortOrder.DESC,
                                ),
                            )
                        )
                    try:
                        result = await asyncio.gather(*tasks)
                    except Exception as e:
                        self.emit_no_wait(Error(e, self))
                        await asyncio.sleep(5)
                        continue
                    node_info: GetBlockSyncStatusResponse = result[0]
                    if block_number is not None:
                        block_data_list: BlockDataListResponse = result[1]
                        transaction_count = sum([len(block.transactions) for block in block_data_list.block_data])
                        self.query_one(f"#{ID.BLOCK_TX_COUNT_5M}").update(
                            f"Transactions(in last 100block): {str(transaction_count)}"
                        )

                    self.query_one(f"#{ID.BLOCK_CURRENT_BLOCK_NUMBER}", Static).update(
                        f"Current Block: {node_info.latest_block_number}"
                    )
                    self.query_one(f"#{ID.BLOCK_IS_SYNCED}", Static).update(f"Is Synced: {node_info.is_synced}")
                    block_number = node_info.latest_block_number
                    elapsed_time = time.time() - start
                    await asyncio.sleep(max(refresh_rate - elapsed_time, 0))

        self.log.debug("Closing background thread")

    async def action_reload_block(self) -> None:
        if self.lock_reload_block.locked():
            return
        async with self.lock_reload_block:
            if self.current_block_number == 0:
                return
            async with TCPConnector(limit=1) as tcp_connector:
                async with ClientSession(connector=tcp_connector, timeout=ClientTimeout(30)) as session:
                    query = ListBlockDataQuery()
                    query.to_block_number = self.current_block_number
                    query.limit = 100
                    query.sort_order = SortOrder.DESC
                    try:
                        block_data_list: BlockDataListResponse = await connector.list_block_data(
                            session,
                            self.base_url,
                            query,
                        )
                    except Exception as e:
                        self.emit_no_wait(Error(e, self))
                        return
                    self.query_one(BlockListTable).update_rows(block_data_list.block_data)
                    self.query_one(f"#{ID.BLOCK_LIST_LOADED_TIME}", Static).update(
                        f"Loaded Time: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}"
                    )

    @property
    def block_detail(self) -> Optional[BlockDataDetail]:
        return self.__block_detail

    @block_detail.setter
    def block_detail(self, block_detail: Optional[BlockDataDetail]) -> None:
        self.__block_detail = block_detail
        self.block_detail_header_widget.refresh()

    async def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        selected_row = self.query_one(BlockListTable).data.get(event.cursor_row)
        if selected_row is None:
            return
        await self.show_selected_block_detail(event.cursor_row)

        if int(selected_row[2]) == 0:
            # If the number of transaction is 0, menu is not pop up.
            return

        self.query_one(Menu).show(
            MenuInstruction(block_number=selected_row[0], block_hash=selected_row[3], selected_row=event.cursor_row)
        )
        self.query(BlockListTable)[0].can_focus = False

    async def show_selected_block_detail(self, selected_row: int):
        selected_row_data = self.query_one(BlockListTable).data.get(selected_row)
        if selected_row is None:
            return
        block_number = selected_row_data[0]
        async with TCPConnector(limit=1) as tcp_connector:
            async with ClientSession(connector=tcp_connector, timeout=ClientTimeout(30)) as session:
                try:
                    block_detail: BlockDataDetail = await connector.get_block_data(
                        session,
                        self.base_url,
                        block_number,
                    )
                except Exception as e:
                    self.emit_no_wait(Error(e, self))
                    return
                self.query_one(BlockDetailView).block_detail = block_detail
