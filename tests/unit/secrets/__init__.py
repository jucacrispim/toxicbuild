# -*- coding: utf-8 -*-

import os
from toxicbuild.secrets import create_settings

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SECRETS_DATA_PATH = os.path.join(DATA_DIR, 'secrets')

os.environ['TOXICSECRETS_SETTINGS'] = os.path.join(
    SECRETS_DATA_PATH, 'toxicsecrets.conf')

create_settings()


# pylint: disable=E402
from toxicbuild.secrets.crypto import Secret  # noqa: E402
Secret.ensure_indexes()
