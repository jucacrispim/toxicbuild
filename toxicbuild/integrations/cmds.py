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

import asyncio
import os
import pkg_resources
import shutil
import sys

from toxicbuild.core.cmd import command, main
from toxicbuild.core.utils import changedir, SettingsPatcher

from . import ensure_indexes, create_settings


PIDFILE = 'toxicintegrations.pid'
LOGFILE = './toxicintegrations.log'

pyrocommand = None


@command
def create(root_dir, access_token='', output_token='', root_user_id='',
           cookie_secret=''):
    """Creates a new toxicbuild integrations environment.

    :param --root_dir: Root directory for toxicbuild integrations.
    :param --access-token: Access token to master's hole.
    :param --output-token: The auth token on the output web api
    :param --root-user-id: The id for the root user of the system.
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
    with open(dest_file, 'r') as fd:
        content = fd.read()

    content = content.replace(
        '{{NOTIFICATIONS_API_TOKEN}}', output_token)
    content = content.replace('{{COOKIE_SECRET}}', cookie_secret)
    content = content.replace('{{HOLE_TOKEN}}', access_token)
    content = content.replace('{{ROOT_USER_ID}}', root_user_id)

    with open(dest_file, 'w') as fd:
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

        create_settings()
        from . import settings

        SettingsPatcher().patch_pyro_settings(settings)

        def setup_fn():
            from toxicbuild.master import (create_settings_and_connect,
                                           create_scheduler)
            create_settings_and_connect()
            create_scheduler()

            from toxicbuild.common import common_setup

            loop = asyncio.get_event_loop()
            loop.run_until_complete(common_setup(settings))

            ensure_indexes()

        print('Starting integrations on port {}'.format(settings.TORNADO_PORT))

        sys.argv = ['pyromanager.py', '']

        from pyrocumulus.commands.base import get_command
        global pyrocommand

        if not pyrocommand:
            pyrocommand = command = get_command('runtornado')()
        else:
            command = pyrocommand

        from .monkey import run
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
        command.setup_fn = setup_fn
        run(command)


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
        from . import settings

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


def _check_conffile(workdir, conffile):
    """Checks if the conffile is inside workdir."""

    absworkdir = os.path.abspath(workdir)
    absconffile = os.path.abspath(conffile)

    return absconffile.startswith(absworkdir)


if __name__ == '__main__':
    main()
