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

# pylint: disable=all

import os
import pkg_resources
from secrets import token_urlsafe
import shutil
import sys
from time import sleep

from mando import main, command

from toxicbuild.core.utils import (
    set_loglevel,
    changedir,
    bcrypt_string,
    daemonize as daemon
)
from . import create_settings, DEFAULT_SETTINGS

PIDFILE = 'toxicsecrets.pid'
LOGFILE = 'toxicsecrets.log'


@command
def create_token(conffile, show_encrypted=False):
    """Creates the access token to the secrets server.

    :param conffile: The path for the toxicsecrets.conf
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
def create_cryto_key(conffile, show_key=False):
    """Creates the key used to encrypt/decrypt the secrets.

    :param conffile: The path for the toxicsecrets.conf
    :param --show-key: Show the encryption key?
    """
    access_token = token_urlsafe()
    encrypted_token = bcrypt_string(access_token)

    with open(conffile, 'rb+') as fd:
        content = fd.read()
        content = content.replace(b'{{CRYPTO_KEY}}', encrypted_token)
        fd.seek(0)
        fd.write(content)

    if show_key:
        print('Created key:{}'.format(encrypted_token))

    return access_token


@command
def create(root_dir, no_token=False):
    """ Creates a new toxicsecrets environment.

    :param --root_dir: Root directory for toxicsecrets.
    :param --no-token: Should we create a access token?
    """
    print('Creating environment on `{}` for toxicsecrets'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicsecrets.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.secrets',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicsecrets.conf')
    shutil.copyfile(template_file, dest_file)
    if no_token:
        access_token = None
    else:
        access_token = create_token(dest_file)

    print('Done!')
    return access_token


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          conffile=None, loglevel='info', pidfile=PIDFILE):
    """Starts a secrets server.

    :param workdir: Work directory for the server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to `toxicsecrets.log`
    :param --stderr: stderr path. Defaults to `toxicsecrets.log`
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicsecrets.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicsecrets.pid``
    """

    print('Starting toxicsecrets')

    _set_toxicsecrets_conf(conffile, workdir)
    create_settings()
    from . import settings

    addr = settings.ADDR
    port = settings.PORT
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

    if daemonize:
        daemon(call=secrets_init, cargs=(addr, port),
               ckwargs={'use_ssl': use_ssl, 'certfile': certfile,
                        'keyfile': keyfile, 'loglevel': loglevel},
               stdout=stdout, stderr=stderr, workdir=workdir, pidfile=pidfile)
    else:
        with changedir(workdir):
            secrets_init(addr, port, use_ssl=use_ssl,
                         certfile=certfile, keyfile=keyfile, loglevel=loglevel)


@command
def stop(workdir, pidfile=PIDFILE, kill=False):
    """ Stops toxicsecrets.

    The instance of toxicsecrets in ``workdir`` will be stopped.

    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicsecrets.pid``
    :param kill: If true, send signum 9, otherwise, 15.
    """

    print('Stopping toxicsecrets')
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
def restart(workdir, pidfile=PIDFILE, loglevel='info'):
    """Restarts toxicsecrets

    The instance of toxicsecrets in ``workdir`` will be restarted.

    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
        ``toxicsecrets.pid``
    :param --loglevel: Level for logging messages.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True, loglevel=loglevel)


def secrets_init(addr, port, use_ssl, certfile, keyfile, loglevel):

    from toxicbuild.secrets.server import run_server
    from toxicbuild.secrets.crypto import Secret
    Secret.ensure_indexes()
    set_loglevel(loglevel)
    run_server(addr, port, use_ssl=use_ssl,
               certfile=certfile, keyfile=keyfile)


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


def _set_toxicsecrets_conf(conffile, workdir):
    if conffile:
        os.environ['TOXICSECRETS_SETTINGS'] = conffile
    else:
        os.environ['TOXICSECRETS_SETTINGS'] = os.path.join(
            workdir, DEFAULT_SETTINGS)


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


if __name__ == '__main__':
    main()
