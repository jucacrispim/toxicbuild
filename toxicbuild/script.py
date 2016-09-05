# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import os
import subprocess
import sys
from mando import command, main
from toxicbuild.master import create as create_master
from toxicbuild.master import create_settings_and_connect
from toxicbuild.master import Slave
from toxicbuild.slave import create as create_slave
from toxicbuild.ui import create as create_ui


class changedir(object):

    def __init__(self, path):
        self.old_dir = os.getcwd()
        self.current_dir = path

    def __enter__(self):
        os.chdir(self.current_dir)

    def __exit__(self, *a, **kw):
        os.chdir(self.old_dir)


@command
def create(root_dir):
    """ Creates a new toxicbuild environment.

    :param --root_dir: Root directory for toxicbuild.
    """

    slave_root = os.path.join(root_dir, 'slave')
    master_root = os.path.join(root_dir, 'master')
    ui_root = os.path.join(root_dir, 'ui')

    # first we create a slave and a master
    slave_token = create_slave(slave_root)
    master_token = create_master(master_root)

    with changedir(master_root):
        create_settings_and_connect()
        loop = asyncio.get_event_loop()
        # now we add this slave to the master
        slave = Slave(name='LocalSlave', token=slave_token,
                      host='localhost', port=7777)

        loop.run_until_complete(slave.save())

    # and finally create a web ui
    create_ui(ui_root, master_token)


@command
def start(workdir, loglevel='error'):
    """Starts toxicbuild.

    Logfiles for the process will be in the file toxic.log

    :param workdir: Work directory for toxicbuild.
    :param --loglevel: Level for logging messages."""

    _call_processes(workdir, loglevel)


@command
def stop(workdir):
    _call_processes(workdir, daemonize=False)


def _call_processes(workdir, loglevel=None, daemonize=True):

    # just pretend you didnt' see this function

    slave_root = os.path.join(workdir, 'slave')
    master_root = os.path.join(workdir, 'master')
    ui_root = os.path.join(workdir, 'ui')

    cmd = sys.argv[0].replace('-script', '')
    slave_cmd = cmd.replace('build', 'slave')
    master_cmd = cmd.replace('build', 'master')
    web_cmd = cmd.replace('build', 'web')

    slave_cmd_line = sys.argv[:]
    slave_cmd_line[0] = slave_cmd
    slave_cmd_line[2] = slave_root
    if daemonize:
        slave_cmd_line.append('--daemonize')

    if loglevel:
        slave_cmd_line.append('--loglevel')
        slave_cmd_line.append(loglevel)

    master_cmd_line = sys.argv[:]
    master_cmd_line[0] = master_cmd
    master_cmd_line[2] = master_root
    if daemonize:
        master_cmd_line.append('--daemonize')
    if loglevel:
        master_cmd_line.append('--loglevel')
        master_cmd_line.append(loglevel)

    web_cmd_line = sys.argv[:]
    web_cmd_line[0] = web_cmd
    web_cmd_line[2] = ui_root
    if daemonize:
        web_cmd_line.append('--daemonize')
    if loglevel:
        web_cmd_line.append('--loglevel')
        web_cmd_line.append(loglevel)

    subprocess.call(slave_cmd_line)
    subprocess.call(master_cmd_line)
    subprocess.call(web_cmd_line)


if __name__ == '__main__':
    main()
