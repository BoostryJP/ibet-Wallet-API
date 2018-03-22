# -*- coding: utf-8 -*-

import sys
import logging

from app import config


logging.basicConfig(level=config.LOG_LEVEL)
LOG = logging.getLogger('API')
LOG.propagate = False

INFO_FORMAT = '[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s'
DEBUG_FORMAT = '[%(asctime)s] [%(process)d] [%(levelname)s] %(message)s [in %(pathname)s:%(lineno)d]'
TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S %z'

if config.APP_ENV == 'live':
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(INFO_FORMAT, TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)

if config.APP_ENV == 'dev' or config.APP_ENV == 'local':
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(DEBUG_FORMAT, TIMESTAMP_FORMAT)
    stream_handler.setFormatter(formatter)
    LOG.addHandler(stream_handler)


def get_logger():
    return LOG
