# -*- coding: utf-8 -*-

# Copyright 2017, 2019 Juca Crispim <juca@poraodojuca.net>

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

# This is a very sketchy thing. We use a set of pre built images (they are
# mapped in the settings file) and each time we run a build we run a
# container based in one of these images.

# The oddest part is that when the container is done we `docker cp` - this is
# why the silly CONTAINER_SLAVE_WORKDIR settings variable exists - the
# source code to the container instead of creating an image with the source
# code.

# This is odd, but there is a reason for that. The files are
# copied to the container instead of create a container with the files
# because I want to have the option to preserve the environment for future
# builds.

import asyncio
import os
from toxicbuild.core.utils import (exec_cmd, interpolate_dict_values,
                                   LoggerMixin)
from toxicbuild.slave import settings
from toxicbuild.slave.build import BuildStep, Builder

DOCKER_CMD = 'docker'
DOCKER_SRC_DIR = os.path.join('/', 'home', '{user}', 'ci', 'src')


class DockerContainerBuilder(Builder):
    """Class to handle docker containers used to run builds inside it.
    """

    def __init__(self, *args, **kwargs):
        self.cname = self._get_name(args[1]['name'], args[2], args[3])

        super().__init__(*args, **kwargs)

        self.docker_cmd = DOCKER_CMD
        self.docker_user = settings.CONTAINER_USER
        self.docker_src_dir = DOCKER_SRC_DIR.format(user=self.docker_user)
        self.image_name = settings.DOCKER_IMAGES[self.platform]
        # are we about to start a container that has a dockerd inside it?
        self._is_dind = self.platform.startswith('docker')

    def _get_name(self, name, workdir, platform):
        name = '{}-{}-{}'.format(
            workdir.replace('/', '-').replace('\\', '-'),
            platform, name)
        return name

    async def __aenter__(self):
        await self.wait_service()
        await self.start_container()
        await self.copy2container()
        return self

    async def __aexit__(self, ext_typ, exc_val, exc_tb):
        await self.rm_from_container()

        await self.kill_container()
        if self.remove_env:

            # used for tests only. do not use this option for real.
            if not getattr(settings,  # pragma no branch
                           'DOCKER_NEVER_REMOVE_CONTAINER', False):
                await self.rm_container()

    def _get_steps(self):
        steps = super()._get_steps()
        return [BuildStepDocker.from_buildstep(s, self.cname) for s in steps]

    async def container_exists(self, only_running=False):
        """Checks if a container named as its ``self.cname``
        already exists

        :param only_running: If True, will look only for running containers.
        """

        msg = 'Checking if container exists'
        self.log(msg, level='debug')

        opt = '' if only_running else '-a'
        cmd = '{} container ps {} --filter name={}'.format(self.docker_cmd,
                                                           opt, self.cname)
        cmd += '| wc -l'
        msg = 'Executing {}'.format(cmd)
        self.log(msg, level='debug')
        ret = await exec_cmd(cmd, cwd='.')
        return int(ret) > 1

    async def is_running(self):
        is_running = await self.container_exists(only_running=True)
        return is_running

    async def service_is_up(self):
        """Check if the docker service is running in the host (slave)
        machine.
        """
        try:
            cmd = '{} info'.format(self.docker_cmd)
            await exec_cmd(cmd, cwd='.')
            r = True
        except Exception:
            r = False

        return r

    def _get_timeout(self):
        try:
            timeout = settings.DOCKER_CONTAINER_TIMEOUT
        except AttributeError:
            timeout = 30

        return timeout

    async def _check_with_timeout(self, coro):
        """Checks until `await coro()` is True. Raises a TimeoutError
        in case the condition is not met.

        :param coro: A coroutine that returns a boolean.
        """
        total = 0.0
        step = 0.1
        timeout = self._get_timeout()
        is_ok = await coro()
        while not is_ok and total < timeout:
            await asyncio.sleep(step)
            total += step
            is_ok = await coro()

    async def wait_service(self):
        """The docker service may start a few seconds after
        the build server is running. Here we wait until
        the docker service is up.
        """
        self.log('Waiting docker service', level='debug')
        await self._check_with_timeout(self.service_is_up)
        self.log('Service is up!', level='debug')

    async def wait_start(self):
        """Waits for a container to start"""

        msg = 'Waiting slave to start'
        self.log(msg, level='debug')
        await self._check_with_timeout(self.is_running)
        self.log('slave started', level='debug')

    def _get_dind_opts(self):
        privileged = '--privileged' if self._is_dind else ''
        vol_name = '{}-volume'.format(self.cname)
        volume = '--mount source={},destination=/var/lib/docker/'.format(
            vol_name) if self._is_dind else ''

        dind_opts = '{} {}'.format(privileged, volume)
        return dind_opts

    async def start_container(self):
        exists = await self.container_exists()
        self.log('Starting container {}'.format(self.cname),
                 level='debug')

        if not exists:
            dind_opts = self._get_dind_opts()
            cmd = '{} run -d -t {} --name {} {}'.format(self.docker_cmd,
                                                        dind_opts,
                                                        self.cname,
                                                        self.image_name)

        else:
            cmd = '{} start {}'.format(self.docker_cmd, self.cname)

        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')
        await self.wait_start()

    async def kill_container(self):
        msg = 'Killing container {}'.format(self.cname)
        self.log(msg, level='debug')
        cmd = '{} kill {}'.format(self.docker_cmd, self.cname)
        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')

    async def rm_container(self):
        msg = 'Removing container {}'.format(self.cname)
        self.log(msg, level='debug')
        cmd = '{} rm {}'.format(self.docker_cmd, self.cname)
        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')

    async def copy2container(self):
        """Recursive copy a directory to the container's src dir."""

        msg = 'Copying files to container {}'.format(self.cname)
        self.log(msg, level='debug')
        cmd = '{} cp {} {}:{}'.format(
            self.docker_cmd, self.workdir, self.cname, self.docker_src_dir)
        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')

        msg = 'Changing files perms in container {}'.format(self.cname)
        self.log(msg, level='debug')
        cmd = '{} exec -u root -t {} chown -R {}:{} {}'.format(
            self.docker_cmd, self.cname, self.docker_user, self.docker_user,
            self.docker_src_dir)
        await exec_cmd(cmd, cwd='.')

    async def rm_from_container(self):
        """Removes the source code of a container that will not be removed.
        """

        msg = 'Removing files from container {}'.format(self.cname)
        self.log(msg, level='debug')
        # removing source dir
        cmd = '{} exec -u root {} rm -rf {}'.format(self.docker_cmd,
                                                    self.cname,
                                                    self.docker_src_dir)
        msg = 'Executing {}'.format(cmd)
        self.log(msg, level='debug')
        await exec_cmd(cmd, cwd='.')


class BuildStepDocker(BuildStep, LoggerMixin):
    """A build step that run the commands inside a docker container.
    """

    def __init__(self, name, command, warning_on_fail=False, timeout=3600,
                 stop_on_fail=False, container_name=None):
        self.container_name = container_name
        self.docker_user = settings.CONTAINER_USER
        self.docker_cmd = DOCKER_CMD
        self.docker_src_dir = DOCKER_SRC_DIR.format(user=self.docker_user)

        super().__init__(name, command, warning_on_fail=warning_on_fail,
                         timeout=timeout, stop_on_fail=stop_on_fail)

    @classmethod
    def from_buildstep(cls, step, container_name):
        return cls(step.name, step.command, step.warning_on_fail,
                   step.timeout, step.stop_on_fail, container_name)

    async def _get_docker_env(self):
        cmd = 'env'
        envvars = ''
        cmd = self._get_docker_cmd(cmd, envvars)
        output = await exec_cmd(cmd, cwd='.')
        lines = [l for l in output.split('\n') if l]
        env = {l.split('=')[0]: l.split('=')[1].strip('\n\r') for l in lines}
        return env

    async def _get_cmd_line_envvars(self, envvars):
        env = await self._get_docker_env()
        envvars = interpolate_dict_values({}, envvars, env)
        var = []

        for k, v in envvars.items():
            var.append('-e "{}={}"'.format(k, v))

        return ' '.join(var)

    def _get_user_opts(self):
        return '-u {}'.format(self.docker_user)

    def _get_docker_cmd(self, cmd, envvars):
        user_opts = self._get_user_opts()
        cmd = '{} exec {} {} -t {} /bin/sh -c "cd {} && {}"'.format(
            self.docker_cmd, user_opts, envvars, self.container_name,
            self.docker_src_dir, cmd)
        return cmd

    async def exec_cmd(self, cmd, cwd, timeout, out_fn, **envvars):
        cmd_envvars = await self._get_cmd_line_envvars(envvars)

        cmd = self._get_docker_cmd(cmd, cmd_envvars)

        self.log('Executing {}'.format(cmd), level='debug')
        output = await exec_cmd(cmd, cwd='.',
                                timeout=self.timeout,
                                out_fn=out_fn, **envvars)
        return output
