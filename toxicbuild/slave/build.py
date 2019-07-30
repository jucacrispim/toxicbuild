# -*- coding: utf-8 -*-

# Copyright 2015-2019 Juca Crispim <juca@poraodojuca.net>

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
from copy import copy
import functools
import os
from uuid import uuid4
from toxicbuild.core.exceptions import ExecCmdError
from toxicbuild.core.utils import (exec_cmd, LoggerMixin, datetime2string,
                                   now, string2datetime, localtime2utc)
from toxicbuild.slave.exceptions import BadPluginConfig


class Builder(LoggerMixin):

    """ A builder executes build steps. Builders are configured in
    the toxicbuild.conf file
    """

    STEP_OUTPUT_BUFF_LEN = 258
    _slave_plugin = None

    def __init__(self, manager, bconf, workdir, platorm='linux-generic',
                 remove_env=True, **envvars):
        """:param manager: instance of :class:`toxicbuild.slave.BuildManager`.
        :param bconf: A dictionary with the builder configuration.
        :param workdir: directory where the steps will be executed.
        :param: platform: When the builder execute is builds.
        :param remove_env: Indicates if the build environment should be
          removed when the build is done.
        :param envvars: Environment variables to be used on the steps.
        """
        self.manager = manager
        self.conf = bconf
        self.name = bconf['name']
        self.workdir = workdir
        self.plugins = self._load_plugins()
        # steps must be defined after plugins
        self.steps = self._get_steps()
        self.platform = platorm
        self.remove_env = remove_env
        self.envvars = envvars
        self._step_output_buff = []
        self._current_step_output_index = None
        self._current_step_output_buff_len = 0

    async def __aenter__(self):
        await self._copy_workdir()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.remove_env:
            await self._remove_tmp_dir()

    @property
    def slave_plugin(self):
        if self._slave_plugin:
            return self._slave_plugin

        # to avoid circular imports
        from toxicbuild.slave.plugins import SlavePlugin
        type(self)._slave_plugin = SlavePlugin
        return SlavePlugin

    def _load_plugins(self):
        """Returns a list of :class:`toxicbuild.slave.plugins.Plugin`
        subclasses based on the plugins listed on the config for a builder.
        """
        plugins_config = self.conf.get('plugins', [])
        plist = []
        for pdict in plugins_config:
            try:
                plugin_class = self.slave_plugin.get_plugin(pdict['name'])
            except KeyError:
                msg = 'Your plugin config {} does not have a name'.format(
                    pdict)
                raise BadPluginConfig(msg)
            del pdict['name']
            plugin = plugin_class(**pdict)
            plist.append(plugin)

        return plist

    def _get_steps(self):
        steps = []

        for plugin in self.plugins:
            steps += plugin.get_steps_before()

        for sdict in self.conf['steps']:
            if isinstance(sdict, str):
                sdict = {'name': sdict,
                         'command': sdict}
            step = BuildStep(**sdict)
            steps.append(step)

        for plugin in self.plugins:
            steps += plugin.get_steps_after()

        return steps

    def _run_in_build_env(self):
        # This is basicaly useless. It is here
        # just because async with self._run_in_build_env() looks
        # better than async with self.
        return self

    async def build(self):
        async with self._run_in_build_env():
            build_info = await self._do_build()
        return build_info

    @asyncio.coroutine
    def _do_build(self):
        build_status = None
        build_info = {'steps': [], 'status': 'running',
                      'started': datetime2string(localtime2utc(now())),
                      'finished': None, 'info_type': 'build_info'}

        yield from self.manager.send_info(build_info)
        last_step_status = None
        last_step_output = None
        last_step_finished = None
        for index, step in enumerate(self.steps):
            self._clear_step_output_buff()
            cmd = yield from step.get_command()
            msg = 'Executing %s' % cmd
            self.log(msg, level='debug')
            local_now = localtime2utc(now())
            step_info = {'status': 'running', 'cmd': cmd,
                         'name': step.name,
                         'started': datetime2string(local_now),
                         'finished': None, 'index': index, 'output': '',
                         'info_type': 'step_info', 'uuid': str(uuid4()),
                         'total_time': None,
                         'last_step_finished': datetime2string(
                             last_step_finished) if last_step_finished
                         else None,
                         'last_step_status': last_step_status}

            yield from self.manager.send_info(step_info)

            envvars = self._get_env_vars()

            out_fn = functools.partial(self._send_step_output_info, step_info)

            step_exec_output = yield from step.execute(
                cwd=self._get_tmp_dir(), out_fn=out_fn,
                last_step_status=last_step_status,
                last_step_output=last_step_output, **envvars)
            step_info.update(step_exec_output)
            yield from self._flush_step_output_buff(step_info['uuid'])

            status = step_info['status']
            msg = 'Finished {} with status {}'.format(cmd, status)
            self.log(msg, level='debug')
            finished = localtime2utc(now())

            last_step_output = step_exec_output
            last_step_status = status
            last_step_finished = finished

            step_info.update({'finished': datetime2string(finished)})
            step_info['total_time'] = (
                finished - string2datetime(step_info['started'])).seconds

            yield from self.manager.send_info(step_info)

            # here is: if build_status is something other than None
            # or success (ie failed) we don't change it anymore, the build
            # is failed anyway.
            if build_status is None or build_status == 'success':
                build_status = status

            build_info['steps'].append(step_info)

            if status in ['fail', 'exception'] and step.stop_on_fail:
                break

        build_info['status'] = build_status
        build_info['total_steps'] = len(self.steps)
        finished = localtime2utc(now())
        build_info['finished'] = datetime2string(finished)

        return build_info

    def _clear_step_output_buff(self):
        self._step_output_buff = []
        self._current_step_output_index = None
        self._current_step_output_buff_len = 0

    @asyncio.coroutine
    def _send_step_output_info(self, step_info, line_index, line):
        self._step_output_buff.append(line)
        self._current_step_output_buff_len += len(line)

        if not self._current_step_output_buff_len > self.STEP_OUTPUT_BUFF_LEN:
            return

        yield from self._flush_step_output_buff(step_info['uuid'])

    @asyncio.coroutine
    def _flush_step_output_buff(self, step_uuid):

        if self._current_step_output_index is None:
            self._current_step_output_index = 0
        else:
            self._current_step_output_index += 1

        msg = {'info_type': 'step_output_info',
               'uuid': step_uuid,
               'output_index': self._current_step_output_index,
               'output': ''.join(self._step_output_buff).strip('\n')}

        yield from self.manager.send_info(msg)
        self._step_output_buff = []
        self._current_step_output_buff_len = 0

    def _get_env_vars(self):
        envvars = copy(self.envvars)
        for plugin in self.plugins:
            envvars.update(plugin.get_env_vars())
        return envvars

    def _get_tmp_dir(self):
        return '{}-{}'.format(os.path.abspath(self.workdir), self.name)

    @asyncio.coroutine
    def _copy_workdir(self):
        """Copy a workdir to a temp dir to run the tests"""

        tmp_dir = self._get_tmp_dir()
        self.log('Copying workdir to {}'.format(tmp_dir), level='debug')

        mkdir_cmd = 'mkdir -p {}'.format(tmp_dir)
        yield from exec_cmd(mkdir_cmd, cwd='.')
        cp_cmd = 'cp -R {}/* {}'.format(self.workdir, tmp_dir)

        self.log('Executing {}'.format(cp_cmd), level='debug')
        yield from exec_cmd(cp_cmd, cwd='.')

    @asyncio.coroutine
    def _remove_tmp_dir(self):
        """Removes the temporary dir"""

        self.log('Removing tmp-dir', level='debug')
        rm_cmd = 'rm -rf {}'.format(self._get_tmp_dir())
        self.log('Executing {}'.format(rm_cmd), level='debug')
        yield from exec_cmd(rm_cmd, cwd='.')


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

    async def get_command(self):
        """Returns the command that will be executed."""

        return self.command

    def __eq__(self, other):
        if not hasattr(other, 'command'):
            return False

        return self.command == other.command

    async def exec_cmd(self, cmd, cwd, timeout, out_fn, **envvars):
        output = await exec_cmd(cmd, cwd=cwd,
                                timeout=self.timeout,
                                out_fn=out_fn, **envvars)
        return output

    @asyncio.coroutine
    def execute(self, cwd, out_fn=None, last_step_status=None,
                last_step_output=None, **envvars):
        """Executes the step command.

        :param cwd: Directory where the command will be executed.
        :param out_fn: Function used to handle each line of the
          command output.
        :param last_step_status: The status of the step before this one
          in the build.
        :param last_step_output: The output of the step before this one
          in the build.
        :param envvars: Environment variables to be used on execution.

        .. note::

            In the case of this method, the params ``last_step_status`` and
            ``last_step_output`` are not used. They are here for the use of
            extentions that may need it. For example, run one command in case
            of one status or another command in case of another status.
        """

        step_status = {}
        try:
            cmd = yield from self.get_command()
            output = yield from self.exec_cmd(cmd, cwd=cwd,
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
