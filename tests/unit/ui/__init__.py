# -*- coding: utf-8 -*-
import os
from toxicbuild.ui import create_settings
from toxicbuild.master import create_settings_and_connect

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
MASTER_DATA_PATH = os.path.join(
    DATA_DIR, '..', '..', 'master', 'data', 'master')
UI_DATA_PATH = os.path.join(DATA_DIR, 'ui')
os.environ['TOXICUI_SETTINGS'] = os.path.join(
    UI_DATA_PATH, 'toxicui.conf')
os.environ['TOXICMASTER_SETTINGS'] = os.path.join(
    MASTER_DATA_PATH, 'toxicmaster.conf')

create_settings()
create_settings_and_connect()
