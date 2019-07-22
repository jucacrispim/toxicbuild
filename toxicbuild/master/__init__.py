# -*- coding: utf-8 -*-

# pylint: disable-all


import asyncio
from asyncio import ensure_future
import os
import pkg_resources
from secrets import token_urlsafe
import shutil
import sys
from time import sleep
from mongomotor import connect
from toxicbuild.core.cmd import command, main
from toxicbuild.core.conf import Settings
from toxicbuild.core.utils import (log, daemonize as daemon,
                                   bcrypt_string, changedir, set_loglevel)

settings = None
dbconn = None
scheduler = None


PIDFILE = 'toxicmaster.pid'
LOGFILE = 'toxicmaster.log'

SCHEDULER_PIDFILE = 'toxicscheduler.pid'
SCHEDULER_LOGFILE = 'toxicscheduler.log'

POLLER_PIDFILE = 'toxicpoller.pid'
POLLER_LOGFILE = 'toxicpoller.log'

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
    from toxicbuild.master.scheduler import TaskScheduler

    global scheduler

    scheduler = TaskScheduler()
    ensure_future(scheduler.start())


@asyncio.coroutine
def toxicinit(server):
    """ Initialize services. """

    # importing here to avoid circular imports
    from toxicbuild.master.build import BuildSet
    from toxicbuild.master.consumers import RepositoryMessageConsumer
    from toxicbuild.master.repository import Repository
    from toxicbuild.master.slave import Slave
    from toxicbuild.master.users import User, Organization

    ensure_indexes(BuildSet, Repository, Slave, User, Organization)

    create_scheduler()

    from toxicbuild.master.exchanges import connect_exchanges

    yield from connect_exchanges()

    log('[init] Boostrap for everyone', level='debug')
    yield from Repository.bootstrap_all()
    if settings.ENABLE_HOLE:
        log('[init] Serving UIHole at {}'.format(settings.HOLE_PORT))
        server.serve()

    message_consumer = RepositoryMessageConsumer()
    message_consumer.run()
    log('[init] Toxicmaster is running!')


async def scheduler_server_init(server):
    """Starts the scheduler server"""

    ensure_future(server.run())
    log('[init] Toxicscheduler is running!')


async def poller_server_init(server):
    """Starts a poller server."""

    ensure_future(server.run())
    log('[init] Toxicpoller is running!')


def run(loglevel):
    """ Runs Toxicbuild master """

    set_loglevel(loglevel)

    create_settings_and_connect()

    from toxicbuild.master.hole import HoleServer

    hole_host = settings.HOLE_ADDR
    hole_port = settings.HOLE_PORT
    try:
        use_ssl = settings.USE_SSL
    except AttributeError:
        use_ssl = False

    try:
        certfile = settings.CERTFILE
    except AttributeError:
        certfile = None

    try:
        keyfile = settings.KEYFILE
    except AttributeError:
        keyfile = None

    server = HoleServer(hole_host, hole_port,
                        use_ssl=use_ssl,
                        certfile=certfile,
                        keyfile=keyfile)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(toxicinit(server))
    try:
        loop.run_forever()
    finally:
        loop.run_until_complete(server.shutdown())


def run_scheduler(loglevel):
    """Runs a scheduler server for toxicbuild master."""

    set_loglevel(loglevel)

    loop = asyncio.get_event_loop()
    create_settings_and_connect()
    from toxicbuild.master.exchanges import connect_exchanges

    loop.run_until_complete(connect_exchanges())

    from toxicbuild.master.scheduler import SchedulerServer

    server = SchedulerServer()

    loop.run_until_complete(scheduler_server_init(server))
    loop.run_forever()


def run_poller(loglevel):
    """Runs a poller server for toxicbuild master."""

    set_loglevel(loglevel)

    loop = asyncio.get_event_loop()
    create_settings_and_connect()
    from toxicbuild.master.exchanges import connect_exchanges
    from toxicbuild.master.pollers import PollerServer
    loop.run_until_complete(connect_exchanges())

    server = PollerServer()

    loop.run_until_complete(poller_server_init(server))
    try:
        loop.run_forever()
    finally:
        server.sync_shutdown()


# console commands

def _run_callable_with_loglevel(call, daemonize, loglevel, stdout, stderr,
                                workdir, pidfile):
    if daemonize:
        daemon(call=call, cargs=(loglevel,), ckwargs={},
               stdout=stdout, stderr=stderr, workdir=workdir, pidfile=pidfile)
    else:
        with changedir(workdir):
            call(loglevel)


def _check_workdir(workdir):
    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)


def _set_toxicmaster_conf(conffile):
    if conffile:
        os.environ['TOXICMASTER_SETTINGS'] = conffile
    else:
        os.environ['TOXICMASTER_SETTINGS'] = DEFAULT_SETTINGS


def _process_exist(pid):
    try:
        os.kill(pid, 0)
        r = True
    except OSError:
        r = False

    return r


def _kill_thing(workdir, pidfile, kill=True):
    with changedir(workdir):
        with open(pidfile) as fd:
            pid = int(fd.read())

        sig = 9 if kill else 15
        os.kill(pid, sig)

        if sig != 9:
            print('Waiting for the process shutdown')
            while _process_exist(pid):
                sleep(0.5)

        os.remove(pidfile)


@command
def start_scheduler(workdir, daemonize=False,
                    stdout=SCHEDULER_LOGFILE, stderr=SCHEDULER_LOGFILE,
                    conffile=None, loglevel='info', pidfile=SCHEDULER_PIDFILE):
    """Starts a scheduler server.

    :param workdir: Work directory for the server.
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
    print('Starting toxicscheduler')
    _check_workdir(workdir)
    _set_toxicmaster_conf(conffile)
    _run_callable_with_loglevel(run_scheduler, daemonize, loglevel,
                                stdout, stderr, workdir, pidfile)


@command
def start_poller(workdir, daemonize=False,
                 stdout=POLLER_LOGFILE, stderr=POLLER_LOGFILE,
                 conffile=None, loglevel='info', pidfile=POLLER_PIDFILE):
    """Starts a poller server.

    :param workdir: Work directory for the server.
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
    print('Starting toxicpoller')
    _check_workdir(workdir)
    _set_toxicmaster_conf(conffile)
    _run_callable_with_loglevel(run_poller, daemonize, loglevel,
                                stdout, stderr, workdir, pidfile)


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          conffile=None, loglevel='info', pidfile=PIDFILE,
          no_scheduler=False, no_poller=False):
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
      ``toxicmaster.pid``
    """

    print('Starting toxicmaster')

    _check_workdir(workdir)
    _set_toxicmaster_conf(conffile)
    _run_callable_with_loglevel(run, daemonize, loglevel,
                                stdout, stderr, workdir, pidfile)


@command
def stop(workdir, pidfile=PIDFILE, kill=False):
    """ Kills toxicmaster.

    :param --workdir: Workdir for master to be killed. Looks for a file
      ``toxicmaster.pid`` inside ``workdir``.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicmaster.pid``
    :param kill: If true, send signum 9, otherwise, 15.
    """

    print('Stopping toxicmaster')
    _kill_thing(workdir, pidfile, kill)


@command
def stop_scheduler(workdir, pidfile=SCHEDULER_PIDFILE, kill=False):
    """Kills toxicmaster scheduler.

    :param --workdir: Workdir for master to be killed. Looks for a file
      ``toxicmaster.pid`` inside ``workdir``.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicscheduler.pid``.
    :param kill: If true, send signum 9, otherwise, 15.
    """

    print('Stopping toxicscheduler')
    _kill_thing(workdir, pidfile, kill)


@command
def stop_poller(workdir, pidfile=POLLER_PIDFILE, kill=False):
    """Kills toxicmaster poller.

    :param --workdir: Workdir for master to be killed. Looks for a file
      ``toxicmaster.pid`` inside ``workdir``.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicpoller.pid``
    :param kill: If true, send signum 9, otherwise, 15.
    """

    print('Stopping toxicpoller')
    _kill_thing(workdir, pidfile, kill)


@command
def restart(workdir, pidfile=PIDFILE, loglevel='info'):
    """Restarts toxicmaster

    The instance of toxicmaster in ``workdir`` will be restarted.
    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
    ``toxicmaster.pid``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True, loglevel=loglevel)


@command
def restart_scheduler(workdir, pidfile=SCHEDULER_PIDFILE, loglevel='info'):
    """Restarts toxicmaster scheduler. The instance of toxicmaster scheduler
    in ``workdir`` will be restarted.

    :param workdir: Workdir for the scheduler to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicscheduler.pid``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    """

    stop_scheduler(workdir, pidfile=pidfile)
    start_scheduler(workdir, pidfile=pidfile, daemonize=True,
                    loglevel=loglevel)


@command
def restart_poller(workdir, pidfile=POLLER_PIDFILE, loglevel='info'):
    """Restarts toxicmaster poller. The instance of toxicmaster poller
    in ``workdir`` will be restarted.

    :param workdir: Workdir for the poller to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicpoller.pid``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    """

    stop_poller(workdir, pidfile=pidfile)
    start_poller(workdir, pidfile=pidfile, daemonize=True,
                 loglevel=loglevel)


@command
def create(root_dir, notifications_token):
    """ Creates a new toxicmaster environment.

    :param --root_dir: Root directory for toxicmaster.
    :param --notification-token: Token for the notifications' web api.
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
    access_token = token_urlsafe()
    encrypted_token = bcrypt_string(access_token)

    # and finally update the config file content with the new generated
    # salt and access token
    with open(dest_file, 'r+') as fd:
        content = fd.read()
        content = content.replace('{{ACCESS_TOKEN}}', encrypted_token)
        content = content.replace('{{NOTIFICATIONS_API_TOKEN}}',
                                  notifications_token)
        fd.seek(0)
        fd.write(content)

    print('Toxicmaster environment created with access token: {}'.format(
        access_token))

    return access_token


async def _create_regular_user(email, password, superuser):
    print('Creating user for authenticated access')

    from toxicbuild.master.users import User  # noqa f401

    if not email:
        email = _ask_thing('email: ')

    if not password:
        password = _ask_thing('password: ')

    user = User(email=email, is_superuser=superuser,
                allowed_actions=['add_repo', 'add_slave', 'remove_user'])
    user.set_password(password)
    await user.save()

    print('User {} created successfully with id: {}'.format(
        user.username, user.id))

    return user


async def _create_limited_user():

    from toxicbuild.master.users import User  # noqa f401

    user = User(email='fake-user@fake-domain.fake',
                allowed_actions=['add_user'])
    await user.save()

    return user


@command
def create_user(configfile, email=None, password=None, superuser=False,
                _limited=False):
    """Creates a superuser in the master.

    :param --email: User's email.
    :param --password: Password for authentication.
    :param --superuser: Indicates if the user is a super user.
      Defaults to False"""

    os.environ[ENVVAR] = configfile
    create_settings_and_connect()

    loop = asyncio.get_event_loop()

    if _limited:
        user = loop.run_until_complete(_create_limited_user())
    else:
        user = loop.run_until_complete(
            _create_regular_user(email, password, superuser))

    return user


@command
def add_slave(configfile, name, host, port, token, owner, use_ssl=False,
              validate_cert=False):
    """Adds a new slave to the master installation.

    :param name: The slave name
    :param host: The slave host.
    :param port: The slave port.
    :param token: The access token to the slave
    :param owner: The id of the slave owner.
    :param use_ssl: Does the slave use secure connection?
    :param validate_cert: Should the slave ssl certificate be validated?
    """

    os.environ[ENVVAR] = configfile
    create_settings_and_connect()

    from toxicbuild.master.slave import Slave
    from toxicbuild.master.users import User

    loop = asyncio.get_event_loop()
    owner = loop.run_until_complete(User.objects.get(id=owner))
    slave = Slave(name=name, host=host, owner=owner, token=token,
                  use_ssl=use_ssl, validate_cert=validate_cert,
                  port=port)

    loop.run_until_complete(slave.save())


def _ask_thing(thing, opts=None):
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
