# -*- coding: utf-8 -*-

import os
from toxicbuild.master import create_settings_and_connect
from toxicbuild.integrations import create_settings
from tests.unit.master import MASTER_DATA_PATH

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
INTEGRATIONS_DATA_PATH = os.path.join(DATA_DIR, 'integrations')
os.environ['TOXICINTEGRATIONS_SETTINGS'] = os.path.join(
    INTEGRATIONS_DATA_PATH, 'toxicintegrations.conf')

os.environ['TOXICMASTER_SETTINGS'] = os.path.join(MASTER_DATA_PATH,
                                                  'toxicmaster.conf')

create_settings_and_connect()
create_settings()
