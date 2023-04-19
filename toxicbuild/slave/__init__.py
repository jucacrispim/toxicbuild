# -*- coding: utf-8 -*-

# pylint: disable-all

from toxicbuild.core.conf import Settings

ENVVAR = 'TOXICSLAVE_SETTINGS'
DEFAULT_SETTINGS = 'toxicslave.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
