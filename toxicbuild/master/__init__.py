# -*- coding: utf-8 -*-

from mongomotor import connect
from toxicbuild.core.conf import Settings

# the api
from toxicbuild.master.repositories import Repository
from toxicbuild.master.build import Slave, Build, Builder


ENVVAR = 'TOXICMASTER_SETTINGS'
DEFAULT_SETTINGS = 'toxicmaster.conf'

settings = Settings(ENVVAR, DEFAULT_SETTINGS)

# here the database connection
dbsettings = settings.DATABASE
dbconn = connect(**dbsettings)

make_pyflakes_happy = [Repository, Slave, Build, Builder]

del make_pyflakes_happy
