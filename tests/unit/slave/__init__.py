# -*- coding: utf-8 -*-

import os
from toxicbuild.slave import create_settings

TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
create_settings()
