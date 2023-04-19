# -*- coding: utf-8 -*-

# pylint: disable=global-statement

from toxicbuild.core.conf import Settings

ENVVAR = 'TOXICPOLLER_SETTINGS'
DEFAULT_SETTINGS = 'toxicpoller.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
