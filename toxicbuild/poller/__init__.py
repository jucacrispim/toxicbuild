# -*- coding: utf-8 -*-

# pylint: disable=global-statement

import asyncio
import os
import pkg_resources
from secrets import token_urlsafe
import shutil
import sys
from time import sleep

from mando import main, command

from toxicbuild.common import common_setup
from toxicbuild.core.conf import Settings
from toxicbuild.core.utils import (
    set_loglevel,
    changedir,
    bcrypt_string,
    daemonize as daemon
)

PIDFILE = 'toxicpoller.pid'
LOGFILE = 'toxicpoller.log'

ENVVAR = 'TOXICPOLLER_SETTINGS'
DEFAULT_SETTINGS = 'toxicpoller.conf'

PIDFILE = 'toxicpoller.pid'
LOGFILE = 'toxicpoller.log'


settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


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


def _set_toxicpoller_conf(conffile):
    if conffile:
        os.environ['TOXICPOLLER_SETTINGS'] = conffile
    else:
        os.environ['TOXICPOLLER_SETTINGS'] = DEFAULT_SETTINGS


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
def create_token(conffile, show_encrypted=False):
    """Creates the access token to the master.

    :param conffile: The path for the toxicpoller.conf
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
def create(root_dir, no_token=False):
    """ Creates a new toxicpoller environment.

    :param --root_dir: Root directory for toxicpoller.
    :param --no-token: Should we create a access token?
    """
    print('Creating environment on `{}` for toxicpoller'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicpoller.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.poller',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicpoller.conf')
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
    """Starts a poller server.

    :param workdir: Work directory for the server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to `toxicpoller.log`
    :param --stderr: stderr path. Defaults to `toxicpoller.log`
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicpoller.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicpoller.pid``
    """

    loop = asyncio.get_event_loop()
    _set_toxicpoller_conf(conffile)
    create_settings()
    loop.run_until_complete(common_setup(settings))

    from toxicbuild.poller.server import run_server

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
        daemon(call=run_server, cargs=(addr, port),
               ckwargs={'use_ssl': use_ssl, 'certfile': certfile,
                        'keyfile': keyfile},
               stdout=stdout, stderr=stderr, workdir=workdir, pidfile=pidfile)
    else:
        set_loglevel(loglevel)

        with changedir(workdir):
            run_server(addr, port, use_ssl=use_ssl,
                       certfile=certfile, keyfile=keyfile)


@command
def stop(workdir, pidfile=PIDFILE, kill=False):
    """ Stops toxicpoller.

    The instance of toxicpoller in ``workdir`` will be stopped.

    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicpoller.pid``
    :param kill: If true, send signum 9, otherwise, 15.
    """

    print('Stopping toxicpoller')
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
    """Restarts toxicpoller

    The instance of toxicpoller in ``workdir`` will be restarted.

    :param workdir: Workdir for master to be killed.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
        ``toxicpoller.pid``
    :param --loglevel: Level for logging messages.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True, loglevel=loglevel)


if __name__ == '__main__':
    main()
