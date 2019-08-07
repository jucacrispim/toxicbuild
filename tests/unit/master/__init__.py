# -*- coding: utf-8 -*-

import asyncio
import atexit
import os
from toxicbuild.master import create_settings_and_connect
from toxicbuild.master import create_scheduler


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
MASTER_DATA_PATH = os.path.join(DATA_DIR, 'master')

os.environ['TOXICMASTER_SETTINGS'] = os.path.join(
    MASTER_DATA_PATH, 'toxicmaster.conf')

create_settings_and_connect()
create_scheduler()
from toxicbuild.master import scheduler  # noqa: f402
scheduler.stop()


from toxicbuild.master.coordination import ToxicZKClient  # noqa: F402


loop = asyncio.get_event_loop()


def clean():
    if ToxicZKClient._zk_client:
        loop.run_until_complete(ToxicZKClient._zk_client.close())


atexit.register(clean)
