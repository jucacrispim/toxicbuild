# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
from copy import copy
import functools
from uuid import uuid4
from toxicbuild.core.exceptions import ExecCmdError
from toxicbuild.core.utils import (exec_cmd, LoggerMixin, datetime2string, now)


class Builder(LoggerMixin):

    """ A builder executes build steps. Builders are configured in
    the toxicbuild.conf file
    """

    def __init__(self, manager, name, workdir, **envvars):
        """:param manager: instance of :class:`toxicbuild.slave.BuildManager`.
        :param name: name for this builder.
        :param workdir: directory where the steps will be executed.
        :param envvars: Environment variables to be used on the steps.
        """
        self.manager = manager
        self.name = name
        self.workdir = workdir
        self.steps = []
        self.plugins = []
        self.envvars = envvars

    @asyncio.coroutine
    def build(self):
        build_status = None
        build_info = {'steps': [], 'status': 'running',
                      'started': datetime2string(now()),
                      'finished': None, 'info_type': 'build_info'}

        yield from self.manager.send_info(build_info)

        self.manager.send_info(build_info)

        for index, step in enumerate(self.steps):
            msg = 'Executing %s' % step.command
            self.log(msg, level='debug')
            step_info = {'status': 'running', 'cmd': step.command,
                         'name': step.name, 'started': datetime2string(now()),
                         'finished': None, 'index': index, 'output': '',
                         'info_type': 'step_info', 'uuid': str(uuid4())}

            yield from self.manager.send_info(step_info)

            envvars = self._get_env_vars()

            out_fn = functools.partial(self._send_step_output_info, step_info)

            step_exec_output = yield from step.execute(cwd=self.workdir,
                                                       out_fn=out_fn,
                                                       **envvars)
            step_info.update(step_exec_output)

            status = step_info['status']
            msg = 'Finished {} with status {}'.format(step.command, status)
            self.log(msg, level='debug')

            step_info.update({'finished': datetime2string(now())})
            yield from self.manager.send_info(step_info)

            # here is: if build_status is something other than None
            # or success (ie failed) we don't change it anymore, the build
            # is failed anyway.
            if build_status is None or build_status == 'success':
                build_status = status

            build_info['steps'].append(step_info)

            if status == 'fail' and step.stop_on_fail:
                break

        build_info['status'] = build_status
        build_info['total_steps'] = len(self.steps)
        build_info['finished'] = datetime2string(now())
        return build_info

    @asyncio.coroutine
    def _send_step_output_info(self, step_info, line_index, line):
        msg = {'info_type': 'step_output_info',
               'uuid': step_info['uuid'], 'output_index': line_index,
               'output': line}

        yield from self.manager.send_info(msg)

    def _get_env_vars(self):
        envvars = copy(self.envvars)
        for plugin in self.plugins:
            envvars.update(plugin.get_env_vars())
        return envvars


class BuildStep:

    def __init__(self, name, command, warning_on_fail=False, timeout=3600,
                 stop_on_fail=False):
        """:param name: name for the command.
        :param cmd: a string the be executed in a shell.
        :param warning_on_fail: Indicates if should have warning status if
          the command fails.
        :param timeout: How long we wait for the command to complete.
        :param stop_on_fail: If True and the step fails the build will stop.
        """
        self.name = name
        self.command = command
        self.warning_on_fail = warning_on_fail
        self.timeout = timeout
        self.stop_on_fail = stop_on_fail

    def __eq__(self, other):
        if not hasattr(other, 'command'):
            return False

        return self.command == other.command

    @asyncio.coroutine
    def execute(self, cwd,  out_fn=None, **envvars):
        """Executes the step command.
        :param cwd: Directory where the command will be executed.
        :param out_fn: Function used to handle each line of the
          command output.
        :param envvars: Environment variables to be used on execution."""

        step_status = {}
        try:
            output = yield from exec_cmd(self.command, cwd=cwd,
                                         timeout=self.timeout,
                                         out_fn=out_fn, **envvars)
            status = 'success'
        except ExecCmdError as e:
            output = e.args[0]
            if self.warning_on_fail:
                status = 'warning'
            else:
                status = 'fail'
        except asyncio.TimeoutError:
            status = 'exception'
            output = '{} has timed out in {} seconds'.format(self.command,
                                                             self.timeout)

        step_status['status'] = status
        step_status['output'] = output

        return step_status
