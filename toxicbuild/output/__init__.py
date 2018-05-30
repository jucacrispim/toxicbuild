# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You shoud have received a copy of the GNU General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import logging
import os
import pkg_resources
import shutil
import sys
from mongomotor import connect
from toxicbuild.core.conf import Settings
from toxicbuild.core.cmd import command, main
from toxicbuild.core.utils import changedir, log, daemonize as daemon


PIDFILE = 'toxicoutput.pid'
LOGFILE = './toxicoutput.log'
ENVVAR = 'TOXICOUTPUT_SETTINGS'
DEFAULT_SETTINGS = 'toxicoutput.conf'

dbconn = None
settings = None


def create_settings_and_connect():
    global settings, dbconn

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)
    dbsettings = settings.DATABASE
    dbconn = connect(**dbsettings)


def _check_conffile(workdir, conffile):
    """Checks if the conffile is inside workdir."""

    absworkdir = os.path.abspath(workdir)
    absconffile = os.path.abspath(conffile)

    return absconffile.startswith(absworkdir)


def output_server_init():
    """Starts the output server"""

    from toxicbuild.output.server import OutputMethodServer

    server = OutputMethodServer()
    asyncio.ensure_future(server.run())
    log('ToxicOutput is running.')


def run_toxicoutput(loglevel):
    loglevel = getattr(logging, loglevel.upper())
    logging.basicConfig(level=loglevel)

    loop = asyncio.get_event_loop()
    output_server_init()
    loop.run_forever()


@command
def create(root_dir):
    """Creates a new toxicbuild output environment.

    :param --root_dir: Root directory for toxicbuild output."""

    print('Creating root_dir `{}` for toxicoutput'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicoutput.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.output',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicoutput.conf')
    shutil.copyfile(template_file, dest_file)


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          conffile=None, loglevel='info', pidfile=PIDFILE):
    """ Starts toxicbuild output.

    :param workdir: Work directory for server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to /dev/null
    :param --stderr: stderr path. Defaults to /dev/null
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicoutput.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicoutput.pid``
    """

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        if conffile:

            is_in_workdir = _check_conffile(workdir, conffile)

            if not is_in_workdir:
                print('Config file must be inside workdir')
                sys.exit(1)

            os.environ['TOXICOUTPUT_SETTINGS'] = os.path.join(
                workdir, conffile)
        else:
            os.environ['TOXICOUTPUT_SETTINGS'] = os.path.join(
                workdir, 'toxicoutput.conf')

        os.environ['TOXICMASTER_SETTINGS'] = os.environ[
            'TOXICOUTPUT_SETTINGS']

        from toxicbuild.master import (
            create_settings_and_connect as create_settings_and_connect_master)
        create_settings_and_connect_master()
        create_settings_and_connect()

        from toxicbuild.master.exchanges import (
            connect_exchanges as connect_master_exchanges)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(connect_master_exchanges())

        from toxicbuild.output.exchanges import connect_exchanges
        loop.run_until_complete(connect_exchanges())

        # this one must be imported so the plugin can run in the
        # output process
        from toxicbuild.integrations.github import GithubCheckRun  # noqa F401
        if daemonize:
            daemon(call=run_toxicoutput, cargs=(loglevel,), ckwargs={},
                   stdout=stdout, stderr=stderr, workdir=workdir,
                   pidfile=pidfile)
        else:
            with changedir(workdir):
                run_toxicoutput(loglevel)


@command
def stop(workdir, pidfile=PIDFILE):
    """ Stops toxicbuid output.

    :param workdir: Work directory for the ui to be killed.
    :param --pidfile: pid file for the process.
    """

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        os.environ['TOXICOUTPUT_SETTINGS'] = os.path.join(
            workdir, 'toxicoutput.conf')

        os.environ['TOXICMASTER_SETTINGS'] = os.environ[
            'TOXICOUTPUT_SETTINGS']

        from toxicbuild.master import (
            create_settings_and_connect as create_settings_and_connect_master)

        create_settings_and_connect_master()
        create_settings_and_connect()

        with changedir(workdir):
            with open(pidfile) as fd:
                pid = int(fd.read())

            os.kill(pid, 9)
            os.remove(pidfile)


@command
def restart(workdir, pidfile=PIDFILE):
    """Restarts toxicbuild output

    The instance of toxicoutput in ``workdir`` will be restarted.
    :param workdir: Workdir for instance to be killed.
    :param --pidfile: Name of the file to use as pidfile.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True)


if __name__ == '__main__':
    main()
