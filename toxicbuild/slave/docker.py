# -*- coding: utf-8 -*-

# Copyright 2017, 2019 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core.utils import exec_cmd, get_envvars, LoggerMixin
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

    def _get_name(self, name, workdir, platform):
        name = '{}-{}-{}'.format(
            workdir.replace('/', '-').replace('\\', '-'),
            platform, name)
        return name

    async def __aenter__(self):
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

    async def wait_start(self):
        msg = 'Waiting slave to start'
        self.log(msg, level='debug')
        try:
            timeout = settings.DOCKER_CONTAINER_TIMEOUT
        except AttributeError:
            timeout = 30
        total = 0.0
        step = 0.1
        is_running = await self.is_running()
        while not is_running and total < timeout:
            await asyncio.sleep(step)
            total += step
            is_running = await self.is_running()

    async def start_container(self):
        exists = await self.container_exists()
        self.log('Starting container {}'.format(self.cname),
                 level='debug')
        if not exists:
            cmd = '{} run -t -d --name {} {}'.format(self.docker_cmd,
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

    def _get_cmd_line_envvars(self, envvars):
        envvars = get_envvars(envvars, use_local_envvars=False)
        var = []

        for k, v in envvars.items():
            var.append('-e "{}={}"'.format(k, v))

        return ' '.join(var)

    async def exec_cmd(self, cmd, cwd, timeout, out_fn, **envvars):
        cmd_envvars = self._get_cmd_line_envvars(envvars)

        user_opts = '-u {}:{}'.format(self.docker_user, self.docker_user)

        cmd = '{} exec {} {} -t {} sh -c "cd {} && {}"'.format(
            self.docker_cmd, user_opts, cmd_envvars, self.container_name,
            self.docker_src_dir, cmd)

        self.log('Executing {}'.format(cmd), level='debug')
        output = await exec_cmd(cmd, cwd='.',
                                timeout=self.timeout,
                                out_fn=out_fn, **envvars)
        return output
