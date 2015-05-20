# -*- coding: utf-8 -*-

import asyncio
import logging
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
def toxicinit():  # pragma no cover
    """ Initialize services. """

    log('[init] Scheduling all')
    yield from Repository.schedule_all()
    if settings.ENABLE_HOLE:
        hole_host = settings.HOLE_ADDR
        hole_port = settings.HOLE_PORT
        server = HoleServer(hole_host, hole_port)
        log('[init] Serving UIHole')
        server.serve()

    log('[init] Toxicbuild is running!')


def run(loglevel):  # pragma no cover
    """ Runs Toxicbuild """

    loglevel = getattr(logging, loglevel.upper())
    logging.basicConfig(level=loglevel)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(toxicinit())
    loop.run_forever()


make_pyflakes_happy = [Slave, Build, Builder, RepositoryRevision]

del make_pyflakes_happy
