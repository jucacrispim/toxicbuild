# -*- coding: utf-8 -*-

import asyncio
import atexit
import os
from toxicbuild.common import common_setup, exchanges
from toxicbuild.master import create_settings_and_connect
from toxicbuild.master import create_scheduler

from toxicbuild.common.coordination import ToxicZKClient  # noqa: F402


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
MASTER_DATA_PATH = os.path.join(DATA_DIR, 'master')

os.environ['TOXICMASTER_SETTINGS'] = os.path.join(
    MASTER_DATA_PATH, 'toxicmaster.conf')

create_settings_and_connect()
create_scheduler()

from toxicbuild.master import scheduler, settings  # noqa: E402
scheduler.stop()


loop = asyncio.get_event_loop()

loop.run_until_complete(common_setup(settings))


def clean():
    if ToxicZKClient._zk_client:
        try:
            loop.run_until_complete(ToxicZKClient._zk_client.close())
        except Exception:
            pass

    try:
        loop.run_until_complete(exchanges.conn.disconnect())
    except Exception:
        pass


atexit.register(clean)
