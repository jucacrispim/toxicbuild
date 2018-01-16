# -*- coding: utf-8 -*-

import os
from toxicbuild.master.integrations import create_settings

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
INTEGRATIONS_DATA_PATH = os.path.join(DATA_DIR, 'integrations')
os.environ['TOXICINTEGRATIONS_SETTINGS'] = os.path.join(
    INTEGRATIONS_DATA_PATH, 'toxicintegrations.conf')

create_settings()
