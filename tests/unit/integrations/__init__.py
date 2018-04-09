# -*- coding: utf-8 -*-

import os
from toxicbuild.integrations import create_settings
from toxicbuild.master import create_settings_and_connect

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
INTEGRATIONS_DATA_PATH = os.path.join(DATA_DIR, 'integrations')
os.environ['TOXICINTEGRATION_SETTINGS'] = os.path.join(
    INTEGRATIONS_DATA_PATH, 'toxicintegrations.conf')

os.environ['TOXICMASTER_SETTINGS'] = os.environ[
    'TOXICINTEGRATION_SETTINGS']

create_settings_and_connect()
# create_settings()
