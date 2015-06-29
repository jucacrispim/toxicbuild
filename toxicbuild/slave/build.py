# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core.exceptions import ExecCmdError
from toxicbuild.core.utils import(exec_cmd, log, datetime2string, now)
from toxicbuild.slave.contextmanagers import change_dir


class Builder:

    """ A builder executes build steps. Builders are configured in
    the toxicbuild.conf file
    """

    def __init__(self, manager, name, workdir):
        """:param manager: instance of :class:`toxicbuild.slave.BuildManager`.
        :param name: name for this builder.
        :param workdir: directory where the steps will be executed
        """
        self.manager = manager
        self.name = name
        self.workdir = workdir
        self.steps = []
        self.plugins = []

    @asyncio.coroutine
    def build(self):
        build_status = None
        build_info = {'steps': [],
                      'status': 'running',
                      'started': datetime2string(now()),
                      'finished': None}
        yield from self.manager.send_info(build_info)

        with change_dir(self.workdir):
            self.manager.send_info(build_info)

            for step in self.steps:
                msg = 'Executing %s' % step.command
                log(msg)
                step_info = {'status': 'running',
                             'cmd': step.command,
                             'name': step.name,
                             'started': datetime2string(now()),
                             'finished': None,
                             'output': ''}

                yield from self.manager.send_info(step_info)

                envvars = self._get_env_vars()
                step_info.update((yield from step.execute(**envvars)))

                msg = 'Finished {} with status {}'.format(step.command,
                                                          step_info['status'])
                log(msg)

                step_info.update({'finished': datetime2string(now())})
                yield from self.manager.send_info(step_info)

                # here is: if build_status is something other than None
                # or success (ie failed) we don't change it anymore, the build
                # is failed anyway.
                if build_status is None or build_status == 'success':
                    build_status = step_info['status']

                build_info['steps'].append(step_info)

        build_info['status'] = build_status
        build_info['total_steps'] = len(self.steps)
        build_info['finished'] = datetime2string(now())
        return build_info

    def _get_env_vars(self):
        envvars = {}
        for plugin in self.plugins:
            envvars.update(plugin.get_env_vars())
        return envvars


class BuildStep:

    def __init__(self, name, cmd):
        """:param name: name for the command
        :param cmd: a string the be executed in a shell
        """
        self.name = name
        self.command = cmd

    def __eq__(self, other):
        if not hasattr(other, 'command'):
            return False

        return self.command == other.command

    @asyncio.coroutine
    def execute(self, **envvars):
        step_status = {}
        try:
            output = yield from exec_cmd(self.command, cwd='.', **envvars)
            status = 'success'
        except ExecCmdError as e:
            output = e.args[0]
            status = 'fail'

        step_status['status'] = status
        step_status['output'] = output

        return step_status
