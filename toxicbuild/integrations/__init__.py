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
import os
import pkg_resources
import shutil
import sys
from pyrocumulus.commands.base import get_command
from toxicbuild.core.conf import Settings
from toxicbuild.core.cmd import command, main
from toxicbuild.core.utils import changedir

PIDFILE = 'toxicintegrations.pid'
LOGFILE = './toxicintegrations.log'
ENVVAR = 'TOXICINTEGRATIONS_SETTINGS'
DEFAULT_SETTINGS = 'toxicintegrations.conf'

settings = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


def _check_conffile(workdir, conffile):
    """Checks if the conffile is inside workdir."""

    absworkdir = os.path.abspath(workdir)
    absconffile = os.path.abspath(conffile)

    return absconffile.startswith(absworkdir)


@command
def create(root_dir):
    """Creates a new toxicbuild integrations environment.

    :param --root_dir: Root directory for toxicbuild integrations."""

    print('Creating root_dir `{}` for toxicintegrations'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicintegrations.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.integrations',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicintegrations.conf')
    shutil.copyfile(template_file, dest_file)


# @command
# def create_github_app(workdir):
#     """Creates a new :class:`~toxicbuild.integrations.github.GithubApp`.

#     To create a new app you must have a GITHUB_APP_ID in your settings file.

#     :param workdir: Work directory for server."""

#     if not os.path.exists(workdir):
#         print('Workdir `{}` does not exist'.format(workdir))
#         sys.exit(1)

#     workdir = os.path.abspath(workdir)
#     with changedir(workdir):
#         sys.path.append(workdir)

#         os.environ['TOXICINTEGRATION_SETTINGS'] = os.path.join(
#             workdir, 'toxicintegrations.conf')
#         os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicintegrations'

#     from toxicbuild.integrations import (
#         create_settings, create_settings_and_connect)
#     loop = asyncio.get_event_loop()
#     create_settings()
#     loop.run_until_complete(create_settings_and_connect())

#     from toxicbuild.integrations.github import GithubApp

#     loop.run_until_complete(GithubApp)


@command
def start(workdir, daemonize=False, stdout=LOGFILE, stderr=LOGFILE,
          conffile=None, loglevel='info', pidfile=PIDFILE):
    """ Starts toxicmaster integrations.

    :param workdir: Work directory for server.
    :param --daemonize: Run as daemon. Defaults to False
    :param --stdout: stdout path. Defaults to /dev/null
    :param --stderr: stderr path. Defaults to /dev/null
    :param -c, --conffile: path to config file. Defaults to None.
      If not conffile, will look for a file called ``toxicintegrations.conf``
      inside ``workdir``
    :param --loglevel: Level for logging messages. Defaults to `info`.
    :param --pidfile: Name of the file to use as pidfile.  Defaults to
      ``toxicintegrations.pid``
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

            os.environ['TOXICINTEGRATION_SETTINGS'] = os.path.join(
                workdir, conffile)
            module = conffile.replace('.conf', '').replace(
                workdir, '').strip('/').replace(os.sep, '.')
            os.environ['PYROCUMULUS_SETTINGS_MODULE'] = module
        else:
            os.environ['TOXICINTEGRATION_SETTINGS'] = os.path.join(
                workdir, 'toxicintegrations.conf')
            os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicintegrations'

        os.environ['TOXICMASTER_SETTINGS'] = os.environ[
            'TOXICINTEGRATION_SETTINGS']

        from toxicbuild.master import (create_settings_and_connect,
                                       create_scheduler)
        create_settings_and_connect()
        create_scheduler()
        create_settings()

        from toxicbuild.master.exchanges import connect_exchanges

        loop = asyncio.get_event_loop()
        loop.run_until_complete(connect_exchanges())

        sys.argv = ['pyromanager.py', '']

        command = get_command('runtornado')()

        command.kill = False
        user_msg = 'Starting ToxicIntegrations. Listening on port {}'
        command.user_message = user_msg
        command.daemonize = daemonize
        command.stderr = stderr
        command.asyncio = True
        command.log_level = loglevel
        command.application = None
        command.stdout = stdout
        command.port = settings.TORNADO_PORT
        command.pidfile = pidfile
        command.run()


@command
def stop(workdir, pidfile=PIDFILE):
    """ Stops toxicmaster integrations.

    :param workdir: Work directory for the ui to be killed.
    :param --pidfile: pid file for the process.
    """

    if not os.path.exists(workdir):
        print('Workdir `{}` does not exist'.format(workdir))
        sys.exit(1)

    workdir = os.path.abspath(workdir)
    with changedir(workdir):
        sys.path.append(workdir)

        os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir,
                                                      'toxicintegrations.conf')
        os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicintegrations'

        create_settings()

        sys.argv = ['pyromanager.py', '']

        command = get_command('runtornado')()

        command.pidfile = pidfile
        command.kill = True
        command.run()


@command
def restart(workdir, pidfile=PIDFILE):
    """Restarts toxicmaster integrations

    The instance of toxicintegrations in ``workdir`` will be restarted.
    :param workdir: Workdir for instance to be killed.
    :param --pidfile: Name of the file to use as pidfile.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True)


if __name__ == '__main__':
    main()
