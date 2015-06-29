# -*- coding: utf-8 -*-

from toxicbuild.core.conf import Settings
from toxicbuild.slave.managers import BuildManager


ENVVAR = 'TOXICSLAVE_SETTINGS'
DEFAULT_SETTINGS = 'toxicslave.conf'

settings = Settings(ENVVAR, DEFAULT_SETTINGS)


make_pyflakes_happy = BuildManager

del make_pyflakes_happy
