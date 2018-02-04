# -*- coding: utf-8 -*-
import os
import configparser

import sqlalchemy as alchemy

APP_ENV = os.environ.get('APP_ENV') or 'local'
INI_FILE = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '../../conf/{}.ini'.format(APP_ENV))

CONFIG = configparser.ConfigParser()
CONFIG.read(INI_FILE)

# PostgreSQL
POSTGRES = CONFIG['postgres']
DB_CONFIG = (POSTGRES['user'], POSTGRES['password'], POSTGRES['host'], POSTGRES['database'])
DATABASE_URL = "postgresql+psycopg2://%s:%s@%s/%s" % DB_CONFIG

engine = alchemy.create_engine(DATABASE_URL, echo=False)

# async process
ASYNC_PROCESS = CONFIG['async_process']
interval_time = ASYNC_PROCESS['interval']
