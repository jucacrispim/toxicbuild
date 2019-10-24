# -*- coding: utf-8 -*-

from toxicbuild.core.conf import Settings

PIDFILE = 'toxicpoller.pid'
LOGFILE = 'toxicpoller.log'

ENVVAR = 'TOXICPOLLER_SETTINGS'
DEFAULT_SETTINGS = 'toxicpoller.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
