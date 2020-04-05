#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from migrate.versioning.shell import main

path = os.path.join(os.path.dirname(__file__), '../')
sys.path.append(path)

from app import config

if __name__ == '__main__':
    main(
        debug='False',
        url=config.DATABASE_URL,
        repository='.'
    )
