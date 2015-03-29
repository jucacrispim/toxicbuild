# -*- coding: utf-8 -*-

from toxicbuild.core.conf import Settings
from mongomotor import connect


ENVVAR = 'TOXICMASTER_SETTINGS'
DEFAULT_SETTINGS = 'toxicmaster.conf'

settings = Settings(ENVVAR, DEFAULT_SETTINGS)

# here the database connection
dbsettings = settings.DATABASE
dbconn = connect(**dbsettings)
