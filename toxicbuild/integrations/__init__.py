# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You shoud have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

# pylint: disable-all


import asyncio
import os
import pkg_resources
import shutil
import sys
from toxicbuild.core.conf import Settings
from toxicbuild.core.cmd import command, main
from toxicbuild.core.utils import changedir, SettingsPatcher

PIDFILE = 'toxicintegrations.pid'
LOGFILE = './toxicintegrations.log'
ENVVAR = 'TOXICINTEGRATIONS_SETTINGS'
DEFAULT_SETTINGS = 'toxicintegrations.conf'

settings = None
pyrocommand = None


def create_settings():
    global settings

    settings = Settings(ENVVAR, DEFAULT_SETTINGS)


def _check_conffile(workdir, conffile):
    """Checks if the conffile is inside workdir."""

    absworkdir = os.path.abspath(workdir)
    absconffile = os.path.abspath(conffile)

    return absconffile.startswith(absworkdir)


@command
def create(root_dir, output_token, cookie_secret):
    """Creates a new toxicbuild integrations environment.

    :param --root_dir: Root directory for toxicbuild integrations.
    :param --output-token: The auth token on the output web api
    :param --cookie-secret: The secret used for secure cookies. This MUST
      be the same secret used in toxicui.
    """

    print('Creating root_dir `{}` for toxicintegrations'.format(root_dir))

    os.makedirs(root_dir)

    template_fname = 'toxicintegrations.conf.tmpl'
    template_dir = pkg_resources.resource_filename('toxicbuild.integrations',
                                                   'templates')
    template_file = os.path.join(template_dir, template_fname)
    dest_file = os.path.join(root_dir, 'toxicintegrations.conf')
    shutil.copyfile(template_file, dest_file)
    with open(dest_file, 'r+') as fd:
        content = fd.read()
        content = content.replace(
            '{{NOTIFICATIONS_API_TOKEN}}', output_token)
        content = content.replace('{{COOKIE_SECRET}}', cookie_secret)
        fd.seek(0)
        fd.write(content)


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
        SettingsPatcher().patch_pyro_settings(settings)

        from pyrocumulus.commands.base import get_command
        from toxicbuild.master.exchanges import connect_exchanges

        loop = asyncio.get_event_loop()
        loop.run_until_complete(connect_exchanges())

        print('Starting integrations on port {}'.format(settings.TORNADO_PORT))

        sys.argv = ['pyromanager.py', '']

        global pyrocommand

        if not pyrocommand:
            pyrocommand = command = get_command('runtornado')()
        else:
            command = pyrocommand

        command.kill = False
        user_msg = 'Starting ToxicIntegrations. Listening on port {}'
        command.user_message = user_msg
        command.daemonize = daemonize
        command.stderr = stderr
        command.asyncio = True
        command.loglevel = loglevel
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

        os.environ['TOXICINTEGRATION_SETTINGS'] = os.path.join(
            workdir, 'toxicintegrations.conf')

        os.environ['TOXICUI_SETTINGS'] = os.path.join(workdir,
                                                      'toxicintegrations.conf')
        os.environ['PYROCUMULUS_SETTINGS_MODULE'] = 'toxicintegrations'

        os.environ['TOXICMASTER_SETTINGS'] = os.environ[
            'TOXICINTEGRATION_SETTINGS']

        from toxicbuild.master import (create_settings_and_connect,
                                       create_scheduler)

        create_settings_and_connect()
        create_scheduler()
        create_settings()
        SettingsPatcher().patch_pyro_settings(settings)

        from pyrocumulus.commands.base import get_command

        sys.argv = ['pyromanager.py', '']

        global pyrocommand

        if not pyrocommand:
            pyrocommand = command = get_command('runtornado')()
        else:
            command = pyrocommand

        command.pidfile = pidfile
        command.kill = True
        command.run()


@command
def restart(workdir, pidfile=PIDFILE, loglevel='info'):
    """Restarts toxicmaster integrations

    The instance of toxicintegrations in ``workdir`` will be restarted.
    :param workdir: Workdir for instance to be killed.
    :param --pidfile: Name of the file to use as pidfile.
    :param --loglevel: Level for logging messages.
    """

    stop(workdir, pidfile=pidfile)
    start(workdir, pidfile=pidfile, daemonize=True, loglevel=loglevel)


if __name__ == '__main__':
    main()
