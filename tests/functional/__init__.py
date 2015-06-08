# -*- coding: utf-8 -*-

import os

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCE_DIR = os.path.join(DATA_DIR, '..', '..', '..')
SCRIPTS_DIR = os.path.join(SOURCE_DIR, 'scripts')
REPO_DIR = os.path.join(DATA_DIR, 'repo')
SLAVE_ROOT_DIR = os.path.join(DATA_DIR, 'slave')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')
