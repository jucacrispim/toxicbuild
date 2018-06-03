# -*- coding: utf-8 -*-
import os
from toxicbuild.ui import create_settings

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
MASTER_DATA_PATH = os.path.join(DATA_DIR, 'ui')
os.environ['TOXICUI_SETTINGS'] = os.path.join(
    MASTER_DATA_PATH, 'toxicui.conf')

create_settings()
