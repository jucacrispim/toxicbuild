# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import os
from secrets import token_urlsafe
import subprocess
import sys
from toxicbuild.core.cmd import command, main
from toxicbuild.integrations import create as create_integrations
from toxicbuild.master import create as create_master
from toxicbuild.master import create_user
from toxicbuild.output import create as create_output, create_auth_token
from toxicbuild.slave import create as create_slave
from toxicbuild.ui import create as create_ui

main._generate_queue = []


@command
def create(root_dir):  # pragma no cover
    """ Creates a new toxicbuild environment.

    Environments for master, slave and ui will be created.

    :param --root_dir: Root directory for toxicbuild.
    """

    slave_root = os.path.join(root_dir, 'slave')
    master_root = os.path.join(root_dir, 'master')
    integrations_root = os.path.join(root_dir, 'integrations')
    output_root = os.path.join(root_dir, 'output')
    ui_root = os.path.join(root_dir, 'ui')
    loop = asyncio.get_event_loop()

    # slave
    slave_token = create_slave(slave_root)
    # output
    create_output(output_root)
    output_token = loop.run_until_complete(create_auth_token(output_root))
    # master
    master_token = create_master(master_root, output_token)
    cookie_secret = token_urlsafe()
    # integrations
    create_integrations(integrations_root, output_token, cookie_secret)

    # a super user to access stuff
    conffile = os.path.join(master_root, 'toxicmaster.conf')
    user = create_user(conffile, superuser=True)

    from toxicbuild.master.slave import Slave

    # create_settings_and_connect()
    # now we add this slave to the master
    slave = Slave(name='LocalSlave', token=slave_token,
                  host='localhost', port=7777, owner=user)

    loop.run_until_complete(slave.save())

    # and finally create a web ui
    create_ui(ui_root, master_token, output_token, str(user.id), cookie_secret)


@command
def start(workdir, loglevel='error'):  # pragma no cover
    """Starts toxicbuild.

    New instances for master, slave and web ui wil be started.

    :param workdir: Work directory for toxicbuild.
    :param --loglevel: Level for logging messages."""

    _call_processes(workdir, loglevel)


@command
def stop(workdir):  # pragma no cover
    """Stops toxicbuild

    The master, slave and web ui instances will be stopped.
    :param workdir: workdir for the instance to be stopped."""

    _call_processes(workdir, daemonize=False)


@command
def restart(workdir, loglevel='info'):
    """Restarts toxicbuild

    The instances of master, slave and web ui in ``workdir`` will be restarted.

    :param workdir: Workdir for master to be killed.
    :param --loglevel: Level for logging messages.
    """

    # daemonize=False because we don't use the --daemonize param for
    # restart as it is ALWAYS daemonized anyway
    _call_processes(workdir, loglevel, daemonize=False)


def _run_slave(workdir, loglevel, daemonize):
    slave_root = os.path.join(workdir, 'slave')
    cmd = sys.argv[0].replace('-script', '')
    slave_cmd = cmd.replace('build', 'slave')
    slave_cmd_line = sys.argv[:]
    slave_cmd_line[0] = slave_cmd
    slave_cmd_line[2] = slave_root
    if daemonize:
        slave_cmd_line.append('--daemonize')

    if loglevel:
        slave_cmd_line.append('--loglevel')
        slave_cmd_line.append(loglevel)

    subprocess.call(slave_cmd_line)


def _run_master(workdir, loglevel, daemonize):
    master_root = os.path.join(workdir, 'master')
    cmd = sys.argv[0].replace('-script', '')
    master_cmd = cmd.replace('build', 'master')

    master_cmd_line = sys.argv[:]
    master_cmd_line[0] = master_cmd
    master_cmd_line[2] = master_root
    if daemonize:
        master_cmd_line.append('--daemonize')
    if loglevel:
        master_cmd_line.append('--loglevel')
        master_cmd_line.append(loglevel)

    subprocess.call(master_cmd_line)


def _run_poller(workdir, loglevel, daemonize):
    master_root = os.path.join(workdir, 'master')
    cmd = sys.argv[0].replace('-script', '')
    master_cmd = cmd.replace('build', 'master')
    poller_cmd_line = sys.argv[:]
    poller_cmd_line[0] = master_cmd
    poller_cmd_line[1] = '{}_poller'.format(poller_cmd_line[1])
    poller_cmd_line[2] = master_root
    if daemonize:
        poller_cmd_line.append('--daemonize')
    if loglevel:
        poller_cmd_line.append('--loglevel')
        poller_cmd_line.append(loglevel)

    subprocess.call(poller_cmd_line)


def _run_scheduler(workdir, loglevel, daemonize):
    master_root = os.path.join(workdir, 'master')
    cmd = sys.argv[0].replace('-script', '')
    master_cmd = cmd.replace('build', 'master')

    scheduler_cmd_line = sys.argv[:]
    scheduler_cmd_line[0] = master_cmd
    scheduler_cmd_line[1] = '{}_scheduler'.format(scheduler_cmd_line[1])
    scheduler_cmd_line[2] = master_root
    if daemonize:
        scheduler_cmd_line.append('--daemonize')
    if loglevel:
        scheduler_cmd_line.append('--loglevel')
        scheduler_cmd_line.append(loglevel)

    subprocess.call(scheduler_cmd_line)


def _run_webui(workdir, loglevel, daemonize):
    ui_root = os.path.join(workdir, 'ui')
    cmd = sys.argv[0].replace('-script', '')
    web_cmd = cmd.replace('build', 'web')

    web_cmd_line = sys.argv[:]
    web_cmd_line[0] = web_cmd
    web_cmd_line[2] = ui_root
    if daemonize:
        web_cmd_line.append('--daemonize')
    if loglevel:
        web_cmd_line.append('--loglevel')
        web_cmd_line.append(loglevel)

    subprocess.call(web_cmd_line)


def _run_output(workdir, loglevel, daemonize):
    output_root = os.path.join(workdir, 'output')
    cmd = sys.argv[0].replace('-script', '')
    output_cmd = cmd.replace('build', 'output')

    output_cmd_line = sys.argv[:]
    output_cmd_line[0] = output_cmd
    output_cmd_line[2] = output_root

    if daemonize:
        output_cmd_line.append('--daemonize')

    if loglevel:
        output_cmd_line.append('--loglevel')
        output_cmd_line.append(loglevel)

    subprocess.call(output_cmd_line)


def _run_integrations(workdir, loglevel, daemonize):
    integrations_root = os.path.join(workdir, 'integrations')
    cmd = sys.argv[0].replace('-script', '')
    integrations_cmd = cmd.replace('build', 'integrations')

    integrations_cmd_line = sys.argv[:]
    integrations_cmd_line[0] = integrations_cmd
    integrations_cmd_line[2] = integrations_root

    if daemonize:
        integrations_cmd_line.append('--daemonize')

    if loglevel:
        integrations_cmd_line.append('--loglevel')
        integrations_cmd_line.append(loglevel)

    subprocess.call(integrations_cmd_line)


def _call_processes(workdir, loglevel=None, daemonize=True):  # pragma no cover

    _run_slave(workdir, loglevel, daemonize)
    _run_master(workdir, loglevel, daemonize)
    _run_poller(workdir, loglevel, daemonize)
    _run_scheduler(workdir, loglevel, daemonize)
    _run_output(workdir, loglevel, daemonize)
    _run_integrations(workdir, loglevel, daemonize)
    _run_webui(workdir, loglevel, daemonize)


if __name__ == '__main__':  # pragma no cover
    main()
