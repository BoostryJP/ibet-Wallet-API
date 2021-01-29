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
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import timezone, timedelta

from web3 import Web3
from web3.middleware import geth_poa_middleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

path = os.path.join(os.path.dirname(__file__), "../")
sys.path.append(path)

from app import config
from app.model.node import Node
from async.lib.misc import wait_all_futures
import log

JST = timezone(timedelta(hours=+9), "JST")
LOG = log.get_logger(process_name="PROCESSOR-BLOCK_SYNC_STATUS")

# 設定の取得
WEB3_HTTP_PROVIDER = config.WEB3_HTTP_PROVIDER
URI = config.DATABASE_URL
WORKER_COUNT = int(config.WORKER_COUNT)
BLOCK_SYNC_STATUS_SLEEP_INTERVAL = config.BLOCK_SYNC_STATUS_SLEEP_INTERVAL
BLOCK_SYNC_STATUS_CALC_PERIOD = config.BLOCK_SYNC_STATUS_CALC_PERIOD
BLOCK_GENERATION_SPEED_THRESHOLD = config.BLOCK_GENERATION_SPEED_THRESHOLD
# 平均ブロック生成間隔 (秒)
EXPECTED_BLOCKS_PER_SEC = 1

# 初期化
web3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER))
web3.middleware_stack.inject(geth_poa_middleware, layer=0)
engine = create_engine(URI, echo=False)
db_session = scoped_session(sessionmaker())
db_session.configure(bind=engine)


class RingBuffer:
    def __init__(self, size, default=None):
        self._next = 0
        self._buffer = [default] * size

    def append(self, data):
        self._buffer[self._next] = data
        self._next = (self._next + 1) % len(self._buffer)

    def peekOldest(self):
        return self._buffer[self._next]


# Watcher
class Watcher:
    def __init__(self):
        pass

    def watch(self):
        pass

    def loop(self):
        try:
            self.watch()
        except Exception as err:  # Exceptionが発生した場合は処理を継続
            LOG.error(err)


class WatchBlockSyncState(Watcher):
    """
    ブロック同期監視。
    ブロックが同期されておらずトランザクションがすぐに取り込まれない状態だと、
    nonce の値が正しく計算されないため同期状態を監視する。
    """

    def __init__(self):
        super().__init__()
        # 起動直後は、監視データが溜まっていないので過去ブロックの情報を観測値として代用する
        block = web3.eth.getBlock(max(web3.eth.blockNumber - BLOCK_SYNC_STATUS_CALC_PERIOD, 0))
        data = {
            "time": block["timestamp"],
            "block_number": block["number"]
        }
        self.history = RingBuffer(BLOCK_SYNC_STATUS_CALC_PERIOD, data)

    def watch(self):
        is_synced = True
        messages = []

        # 接続先ノードのチェーンが遅れており、最新のブロックを取り込んでいる途中か判定
        syncing = web3.eth.syncing
        if syncing:
            remaining_blocks = syncing["highestBlock"] - syncing["currentBlock"]
            # 1ブロックだけ遅れている場合はすぐに最新化されると想定して正常扱い
            if remaining_blocks > 1:
                is_synced = False
                messages.append(f"highestBlock={syncing['highestBlock']}, currentBlock={syncing['currentBlock']}")

        # ブロックナンバー増加チェック
        # 直近 BLOCK_SYNC_STATUS_CALC_PERIOD 回の監視中に増加したブロックナンバーが、
        # 理論値の BLOCK_GENERATION_SPEED_THRESHOLD % を下回ればエラー
        data = {
            "time": time.time(),
            "block_number": web3.eth.blockNumber
        }
        old_data = self.history.peekOldest()
        elapsed_time = data["time"] - old_data["time"]
        generated_block_count = data["block_number"] - old_data["block_number"]
        generated_block_count_threshold = \
            elapsed_time / EXPECTED_BLOCKS_PER_SEC * BLOCK_GENERATION_SPEED_THRESHOLD / 100
        if generated_block_count < generated_block_count_threshold:
            is_synced = False
            messages.append(f"{generated_block_count} blocks in {int(elapsed_time)} sec")

        self.history.append(data)

        # DB更新
        status_changed = False
        node = db_session.query(Node).first()
        if node is None:
            node = Node()
            node.is_synced = is_synced
            db_session.merge(node)
            db_session.commit()
        elif node.is_synced != is_synced:
            node.is_synced = is_synced
            db_session.commit()
            status_changed = True

        # ブロック同期状態の変化に応じてログ出力
        if status_changed:
            if is_synced:
                LOG.info("Block synchronization is working.")
            else:
                LOG.error("Block synchronization is down: %s", messages)
        elif not is_synced:
            # 一度エラーログを出力した後は、ワーニングレベルでログを出す
            LOG.warning("Block synchronization is down: %s", messages)


def main():
    watchers = [
        WatchBlockSyncState(),
    ]

    e = ThreadPoolExecutor(max_workers=WORKER_COUNT)
    LOG.info("Service started successfully")

    while True:
        start_time = time.time()

        fs = []
        for watcher in watchers:
            fs.append(e.submit(watcher.loop))
        wait_all_futures(fs)

        elapsed_time = time.time() - start_time
        LOG.info("[LOOP] finished in {} secs".format(elapsed_time))

        time.sleep(max(BLOCK_SYNC_STATUS_SLEEP_INTERVAL - elapsed_time, 0))


if __name__ == "__main__":
    main()
