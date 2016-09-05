# -*- coding: utf-8 -*-

import asyncio
try:
    from asyncio import ensure_future
except ImportError:  # pragma no cover
    from asyncio import async as ensure_future

import logging
import os
import pkg_resources
import shutil
from mando import command, main
from mongomotor import connect
from toxicbuild.core.conf import Settings
from toxicbuild.core.utils import log, daemonize as daemon
from toxicbuild.master.scheduler import TaskScheduler
# the api
from toxicbuild.master.repository import (Repository, RepositoryRevision,
                                          RepositoryBranch)
from toxicbuild.master.build import Build, Builder, BuildSet
from toxicbuild.master.slave import Slave

PIDFILE = 'toxicmaster.pid'

ENVVAR = 'TOXICMASTER_SETTINGS'
DEFAULT_SETTINGS = 'toxicmaster.conf'

settings = None
dbconn = None
scheduler = None


def create_settings_and_connect():
    global settings, dbconn

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
    # here the database connection
    dbsettings = settings.DATABASE
    dbconn = connect(**dbsettings)


def ensure_indexex():
    BuildSet.ensure_indexes()


def create_scheduler():
    global scheduler

    scheduler = TaskScheduler()
    ensure_future(scheduler.start())


# script


@asyncio.coroutine
def toxicinit():  # pragma no cover
    """ Initialize services. """

    create_settings_and_connect()
    ensure_indexex()
    create_scheduler()

    # importing here to avoid circular imports
    from toxicbuild.master.hole import HoleServer

    log('[init] Scheduling all')
    yield from Repository.schedule_all()
    if settings.ENABLE_HOLE:
        hole_host = settings.HOLE_ADDR
        hole_port = settings.HOLE_PORT
        server = HoleServer(hole_host, hole_port)
        log('[init] Serving UIHole at {}'.format(settings.HOLE_PORT))
        server.serve()

    log('[init] Toxicbuild is running!')


def run(loglevel):  # pragma no cover
    """ Runs Toxicbuild master """

    loglevel = getattr(logging, loglevel.upper())
    logging.basicConfig(level=loglevel)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(toxicinit())
    loop.run_forever()


@command
def start(workdir, daemonize=False, stdout='/dev/null', stderr='/dev/null',
          conffile=None, loglevel='info', pidfile=PIDFILE):
    """ Starts toxicmaster.

    :param workdir: Work directory for server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to /dev/null
    :param --stderr: stderr path. Defaults to /dev/null
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicmaster.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    if conffile:
        os.environ['TOXICMASTER_SETTINGS'] = conffile
    else:
        os.environ['TOXICMASTER_SETTINGS'] = DEFAULT_SETTINGS

    if daemonize:
        daemon(call=run, cargs=(loglevel,), ckwargs={}, stdout=stdout,
               stderr=stderr, workdir=workdir, pidfile=pidfile)
    else:
        os.chdir(workdir)
        run(loglevel)


@command
def stop(workdir, pidfile=PIDFILE):
    """ Kills toxicmaster.

    :param --workdir: Workdir for master to be killed. Looks for a file
      ``toxicmaster.pid`` inside ``workdir``.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    os.chdir(workdir)
    with open(pidfile) as fd:
        pid = int(fd.read())

    os.kill(pid, 9)
    os.remove(pidfile)


@command
def create(root_dir):
    """ Creates a new toxicmaster environment.

    :param --root_dir: Root directory for toxicmaster.
    """
    print('Creating root_dir {}'.format(root_dir))

    os.mkdir(root_dir)

    # :/
    # need fake settings here or pkg_resources does not work.
    fakesettings = os.path.join(root_dir, 'fakesettings.py')
    with open(fakesettings, 'w') as f:
        f.write('DATABASE = {}')
    os.environ['TOXICMASTER_SETTINGS'] = fakesettings

    template_fname = 'toxicmaster.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.master',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicmaster.conf')
    shutil.copyfile(template_file, dest_file)
    os.remove(fakesettings)


make_pyflakes_happy = [Slave, Build, Builder, RepositoryRevision,
                       BuildSet, RepositoryBranch, Repository]

del make_pyflakes_happy


if __name__ == '__main__':
    main()
