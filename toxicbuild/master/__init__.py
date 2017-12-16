# -*- coding: utf-8 -*-

import asyncio
try:
    from asyncio import ensure_future
except ImportError:
    from asyncio import async as ensure_future

import logging
import os
import pkg_resources
import shutil
import sys
from uuid import uuid4
from mongomotor import connect
from toxicbuild.core.cmd import command, main
from toxicbuild.core.conf import Settings
from toxicbuild.core.utils import (log, daemonize as daemon, bcrypt,
                                   bcrypt_string, changedir)
from toxicbuild.master.scheduler import TaskScheduler

settings = None
dbconn = None
scheduler = None


PIDFILE = 'toxicmaster.pid'
LOGFILE = 'toxicmaster.log'

ENVVAR = 'TOXICMASTER_SETTINGS'
DEFAULT_SETTINGS = 'toxicmaster.conf'


def create_settings_and_connect():
    global settings, dbconn

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
    # here the database connection
    dbsettings = settings.DATABASE
    dbconn = connect(**dbsettings)


def ensure_indexes(*classes):
    for cls in classes:
        cls.ensure_indexes()


def create_scheduler():
    global scheduler

    scheduler = TaskScheduler()
    ensure_future(scheduler.start())


@asyncio.coroutine
def toxicinit():
    """ Initialize services. """

    create_settings_and_connect()

    # importing here to avoid circular imports
    from toxicbuild.master.build import BuildSet
    from toxicbuild.master.hole import HoleServer
    from toxicbuild.master.repository import Repository
    from toxicbuild.master.slave import Slave
    from toxicbuild.master.users import User, Organization

    ensure_indexes(BuildSet, Repository, Slave, User, Organization)
    create_scheduler()

    log('[init] Scheduling all')
    yield from Repository.schedule_all()
    if settings.ENABLE_HOLE:
        hole_host = settings.HOLE_ADDR
        hole_port = settings.HOLE_PORT
        server = HoleServer(hole_host, hole_port)
        log('[init] Serving UIHole at {}'.format(settings.HOLE_PORT))
        server.serve()

    log('[init] Toxicbuild is running!')


def run(loglevel):
    """ Runs Toxicbuild master """

    loglevel = getattr(logging, loglevel.upper())
    logging.basicConfig(level=loglevel)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(toxicinit())
    loop.run_forever()


# console commands


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
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

    print('Starting toxicmaster')
    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    if conffile:
        os.environ['TOXICMASTER_SETTINGS'] = conffile
    else:
        os.environ['TOXICMASTER_SETTINGS'] = DEFAULT_SETTINGS

    if daemonize:
        daemon(call=run, cargs=(loglevel,), ckwargs={}, stdout=stdout,
               stderr=stderr, workdir=workdir, pidfile=pidfile)
    else:
        with changedir(workdir):
            run(loglevel)


@command
def stop(workdir, pidfile=PIDFILE):
    """ Kills toxicmaster.

    :param --workdir: Workdir for master to be killed. Looks for a file
      ``toxicmaster.pid`` inside ``workdir``.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicslave.pid``
    """

    print('Stopping toxicmaster')
    with changedir(workdir):
        with open(pidfile) as fd:
            pid = int(fd.read())

        os.kill(pid, 9)
        os.remove(pidfile)


@command
def restart(workdir, pidfile=PIDFILE):
    """Restarts toxicmaster

    The instance of toxicmaster in ``workdir`` will be restarted.
    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
    ``toxicmaster.pid``
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True)


@command
def create(root_dir):
    """ Creates a new toxicmaster environment.

    :param --root_dir: Root directory for toxicmaster.
    """
    print('Creating root_dir `{}` for toxicmaster'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicmaster.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.master',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicmaster.conf')
    shutil.copyfile(template_file, dest_file)

    # here we create a bcrypt salt and a access token for authentication.
    salt = bcrypt.gensalt(8)
    access_token = str(uuid4())
    encrypted_token = bcrypt_string(access_token, salt)

    # and finally update the config file content with the new generated
    # salt and access token
    with open(dest_file, 'r+') as fd:
        content = fd.read()
        content = content.replace('{{BCRYPT_SALT}}', salt.decode())
        content = content.replace('{{ACCESS_TOKEN}}', encrypted_token)
        fd.seek(0)
        fd.write(content)

    print('Toxicmaster environment created with access token: {}'.format(
        access_token))

    return access_token


@command
def create_user(configfile, email=None, password=None, superuser=False):
    """Creates a superuser in the master.

    :param --email: User's email.
    :param --password: Password for authentication.
    :param --superuser: Indicates if the user is a super user.
      Defaults to False"""

    print('Creating user for authenticated access')

    os.environ[ENVVAR] = configfile
    create_settings_and_connect()

    from toxicbuild.master.users import User  # noqa f401

    if not email:
        email = _ask_thing('email: ')

    if not password:
        password = _ask_thing('password: ')

    user = User(email=email, is_superuser=superuser,
                allowed_actions=['add_repo', 'add_slave', 'remove_user'])
    user.set_password(password)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(user.save())
    print('User {} created successfully'.format(user.username))


def _ask_thing(thing, opts=[]):
    if opts:
        thing += '[' + '/'.join(opts) + ']'

    response = input(thing)
    while not response:
        response = input(thing)
        if opts:
            if response.lower() not in opts:
                response = ''

    return response


if __name__ == '__main__':
    main()
