# -*- coding: utf-8 -*-

import asyncio
import atexit
import os

from toxicbuild.common import common_setup, exchanges
from toxicbuild.poller import create_settings

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
POLLER_DATA_PATH = os.path.join(DATA_DIR, 'poller')

os.environ['TOXICPOLLER_SETTINGS'] = os.path.join(
    POLLER_DATA_PATH, 'toxicpoller.conf')

create_settings()

from toxicbuild.poller import settings  # noqa

loop = asyncio.get_event_loop()
loop.run_until_complete(common_setup(settings))

from toxicbuild.common.coordination import ToxicZKClient  # noqa: F402


def clean():
    if ToxicZKClient._zk_client:
        loop.run_until_complete(ToxicZKClient._zk_client.close())

    loop.run_until_complete(exchanges.conn.disconnect())


atexit.register(clean)
