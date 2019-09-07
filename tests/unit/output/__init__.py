# -*- coding: utf-8 -*-

import os
from toxicbuild.master import create_settings_and_connect
from toxicbuild.output import create_settings_and_connect as create_settings
from tests.unit.master import MASTER_DATA_PATH
from tests.unit.integrations import INTEGRATIONS_DATA_PATH

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
OUTPUT_DATA_PATH = os.path.join(DATA_DIR, 'output')
os.environ['TOXICOUTPUT_SETTINGS'] = os.path.join(
    OUTPUT_DATA_PATH, 'toxicoutput.conf')

os.environ['TOXICMASTER_SETTINGS'] = os.path.join(MASTER_DATA_PATH,
                                                  'toxicmaster.conf')

os.environ['TOXICINTEGRATIONS_SETTINGS'] = os.path.join(
    INTEGRATIONS_DATA_PATH, 'toxicintegrations.conf')

create_settings_and_connect()
create_settings()


from toxicbuild.output import settings  # noqa
