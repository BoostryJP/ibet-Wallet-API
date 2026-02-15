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

import contextlib
import contextvars
import logging
import sys
from typing import Any, Mapping, cast

from app import config
from logger import NOTICE, SystemLogger

_parent_process_name: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "batch_parent_process_name", default=None
)


@contextlib.contextmanager
def parent_process(process_name: str | None):
    token = _parent_process_name.set(process_name)
    try:
        yield
    finally:
        _parent_process_name.reset(token)


class _BatchContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        process_name = getattr(record, "process_name", None) or record.name
        parent_name = _parent_process_name.get()
        record.process_name = process_name
        record.parent_process_name = parent_name
        record.process_path = (
            f"{parent_name} > {process_name}" if parent_name else str(process_name)
        )
        return True


class BatchLoggerAdapter(logging.LoggerAdapter[SystemLogger]):
    """Logger adapter that injects a fixed batch `process_name` per module."""

    def __init__(self, logger: SystemLogger, process_name: str):
        super().__init__(logger, {"process_name": process_name})

    def process(self, msg: Any, kwargs: Mapping[str, Any]):
        kwargs = dict(kwargs)
        extra = kwargs.get("extra")
        empty_extra: dict[str, object] = {}
        base_extra: Mapping[str, object] = (
            self.extra if self.extra is not None else empty_extra
        )
        if extra is None:
            kwargs["extra"] = dict(base_extra)
        else:
            merged = dict(base_extra)
            if isinstance(extra, Mapping):
                merged.update(cast(Mapping[str, object], extra))
            kwargs["extra"] = merged
        return msg, kwargs

    def notice(self, msg: str, *args: Any, **kwargs: Any):
        self.log(NOTICE, msg, *args, **kwargs)


def _configure_base_logger() -> SystemLogger:
    logging.setLoggerClass(SystemLogger)

    logging.getLogger("pyroscope").setLevel(logging.ERROR)
    logging.getLogger("py_spy").setLevel(logging.ERROR)
    logging.getLogger("opentelemetry").setLevel(logging.ERROR)

    base_logger = cast(SystemLogger, logging.getLogger("ibet_wallet_batch"))
    base_logger.propagate = False

    if not getattr(base_logger, "_ibet_wallet_batch_configured", False):
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.addFilter(_BatchContextFilter())
        formatter = logging.Formatter(
            config.INFO_LOG_FORMAT.format("[%(process_path)s]"),
            config.LOG_TIMESTAMP_FORMAT,
        )
        stream_handler.setFormatter(formatter)
        base_logger.addHandler(stream_handler)
        setattr(base_logger, "_ibet_wallet_batch_configured", True)

    return base_logger


def get_logger(process_name: str) -> BatchLoggerAdapter:
    base_logger = _configure_base_logger()
    return BatchLoggerAdapter(base_logger, process_name=process_name)
