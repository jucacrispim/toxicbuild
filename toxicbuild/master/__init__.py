# -*- coding: utf-8 -*-

import asyncio
from mongomotor import connect
from toxicbuild.core.utils import log
from toxicbuild.core.conf import Settings

# the api
from toxicbuild.master.repositories import Repository, RepositoryRevision
from toxicbuild.master.build import Slave, Build, Builder
from toxicbuild.master.hole import HoleServer


ENVVAR = 'TOXICMASTER_SETTINGS'
DEFAULT_SETTINGS = 'toxicmaster.conf'

settings = Settings(ENVVAR, DEFAULT_SETTINGS)

# here the database connection
dbsettings = settings.DATABASE
dbconn = connect(**dbsettings)


@asyncio.coroutine
def run():  # pragma no cover
    """ Runs Toxicbuild """

    log('[main] Scheduling all')
    yield from Repository.schedule_all()
    if settings.ENABLE_HOLE:
        hole_host = settings.HOLE_ADDR
        hole_port = settings.HOLE_PORT
        server = HoleServer(hole_host, hole_port)
        log('[main] Serving UIHole')
        server.serve()

    log('[main] Toxicbuild is running!')

make_pyflakes_happy = [Slave, Build, Builder]

del make_pyflakes_happy
