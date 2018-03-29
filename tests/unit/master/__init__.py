# -*- coding: utf-8 -*-

import os
from toxicbuild.master import create_settings_and_connect
from toxicbuild.master import create_scheduler
from tests import MASTER_ROOT_DIR


os.environ['TOXICMASTER_SETTINGS'] = os.path.join(MASTER_ROOT_DIR,
                                                  'toxicmaster.conf')


create_settings_and_connect()
create_scheduler()
from toxicbuild.master import scheduler  # noqa: f402
scheduler.stop()


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
MASTER_DATA_PATH = os.path.join(DATA_DIR, 'master')
os.environ['TOXICMASTER_SETTINGS'] = os.path.join(
    MASTER_DATA_PATH, 'toxicmaster.conf')

create_settings_and_connect()
