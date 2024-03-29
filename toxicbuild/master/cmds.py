# -*- coding: utf-8 -*-
# Copyright 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable-all

import asyncio
import os
import sys
from time import sleep
import pkg_resources
from secrets import token_urlsafe
import shutil

from toxicbuild.common import common_setup
from toxicbuild.core.cmd import command, main
from toxicbuild.core.utils import (daemonize as daemon,
                                   bcrypt_string, changedir, set_loglevel, log)
from . import (
    ENVVAR,
    DEFAULT_SETTINGS,
    create_settings_and_connect,
    create_scheduler,
    ensure_indexes)


PIDFILE = 'toxicmaster.pid'
LOGFILE = 'toxicmaster.log'


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
def create_token(conffile, show_encrypted=False):
    """Creates the access token to the master.

    :param conffile: The path for the toxicmaster.conf
    :param --show-encrypted: Show the encrypted token?
    """
    access_token = token_urlsafe()
    encrypted_token = bcrypt_string(access_token)

    with open(conffile, 'r+') as fd:
        content = fd.read()
        content = content.replace('{{ACCESS_TOKEN}}', encrypted_token)
        fd.seek(0)
        fd.write(content)

    if show_encrypted:
        print('Created encrypted token:{}'.format(encrypted_token))
    print('Created access token:{}'.format(access_token))
    return access_token


@command
def create(root_dir, notifications_token='', poller_token='', no_token=False):
    """ Creates a new toxicmaster environment.

    :param --root_dir: Root directory for toxicmaster.
    :param --notifications-token: The auth token for the output web api.
    :param --poller-token: The auth token for the poller.
    :param --no-token: Should we create a access token?
    """
    print('Creating environment on `{}` for toxicmaster'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicmaster.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.master',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicmaster.conf')
    shutil.copyfile(template_file, dest_file)
    if no_token:
        access_token = None
    else:
        access_token = create_token(dest_file)

    with open(dest_file, 'r') as fd:
        content = fd.read()

    content = content.replace('{{NOTIFICATIONS_API_TOKEN}}',
                              notifications_token)
    content = content.replace('{{POLLER_TOKEN}}', poller_token)
    with open(dest_file, 'w') as fd:
        fd.write(content)

    print('Done!')
    return access_token


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


def run(loglevel):
    """ Runs Toxicbuild master """

    set_loglevel(loglevel)

    create_settings_and_connect()

    from toxicbuild.master.hole import HoleServer

    from . import settings

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


async def toxicinit(server):
    """ Initialize services. """

    from . import settings
    # importing here to avoid circular imports
    from toxicbuild.master.build import BuildSet
    from toxicbuild.master.consumers import RepositoryMessageConsumer
    from toxicbuild.master.repository import Repository
    from toxicbuild.master.slave import Slave
    from toxicbuild.master.users import User, Organization

    ensure_indexes(BuildSet, Repository, Slave, User, Organization)

    create_scheduler()

    await common_setup(settings)

    log('[init] Boostrap for everyone', level='debug')
    await Repository.bootstrap_all()
    if settings.ENABLE_HOLE:
        log('[init] Serving UIHole at {}'.format(settings.HOLE_PORT))
        server.serve()

    message_consumer = RepositoryMessageConsumer()
    message_consumer.run()
    log('[init] Toxicmaster is running!')


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
