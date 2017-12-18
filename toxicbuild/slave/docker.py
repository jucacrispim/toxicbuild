# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core.exceptions import ConfigError
from toxicbuild.core.utils import exec_cmd, LoggerMixin
from toxicbuild.slave import settings
from toxicbuild.slave.client import ContainerBuildClient


class DockerContainerBuilder(LoggerMixin):
    """Class to handle docker containers used to run builds inside it.
    """

    # really ugly signature, right?
    def __init__(self, manager, platform, repo_url, vcs_type, branch,
                 named_tree, builder_name, source_dir, remove_env=True):
        """Constructor for DockerContainer.

        :param manager: instance of :class:`toxicbuild.slave.BuildManager.`
        :param platform: Platform where the build will be executed
        :param repo_url: The repository URL
        :param vcs_type: Type of vcs used in the repository.
        :param branch: Which branch to use in the build.
        :param named_tree: A tag, commit, branch name...
        :param builder_name: The builder that will execute the build
        :param source_dir: Directory with the source code in the host
        :param remove_env: Should the container be removed when the build is
          done?"""

        self.build_data_body = {'repo_url': repo_url,
                                'vcs_type': vcs_type,
                                'branch': branch,
                                'named_tree': named_tree,
                                'builder_name': builder_name}
        self.build_data = {'action': 'build',
                           'body': self.build_data_body}

        self.manager = manager
        self.source_dir = source_dir
        self.builder_name = builder_name
        self.container_slave_workdir = settings.CONTAINER_SLAVE_WORKDIR
        self.platform = platform
        self.image_name = settings.DOCKER_IMAGES[self.platform]
        self.remove_env = remove_env
        self.docker_cmd = 'docker'
        self.client = ContainerBuildClient(self.build_data, self)

    @property
    def name(self):
        name = '{}-{}-{}'.format(
            self.source_dir.replace('/', '-').replace('\\', '-'),
            self.platform, self.builder_name)
        return name

    async def __aenter__(self):
        await self.start_container()
        await self.copy2container()
        await self.client.__aenter__()
        return self

    async def __aexit__(self, ext_typ, exc_val, exc_tb):
        await self.client.__aexit__(ext_typ, exc_val, exc_tb)
        if not self.remove_env:
            # removes the source code from the container
            await self.rm_from_container()

        await self.kill_container()

        if self.remove_env:
            await self.rm_container()

    async def container_exists(self):
        """Checks if a container named as its ``self.name``
        already exists"""

        msg = 'Checking if container exists'
        self.log(msg, level='debug')
        cmd = '{} container ps -a --filter name={}'.format(self.docker_cmd,
                                                           self.name)
        cmd += '| wc -l'
        msg = 'Executing {}'.format(cmd)
        self.log(msg, level='debug')
        ret = await exec_cmd(cmd, cwd='.')
        return int(ret) > 1

    async def is_running(self):
        try:
            async with self.client:
                is_running = await self.client.healthcheck()
        except Exception:
            is_running = False
        return is_running

    async def wait_start(self):
        msg = 'Waiting slave to start'
        self.log(msg, level='debug')
        try:
            timeout = settings.DOCKER_CONTAINER_TIMEOUT
        except ConfigError:
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
        self.log('Starting container {}'.format(self.name),
                 level='debug')
        if not exists:
            cmd = '{} run -t -d --name {} {}'.format(self.docker_cmd,
                                                     self.name,
                                                     self.image_name)

        else:
            cmd = '{} start {}'.format(self.docker_cmd, self.name)

        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')
        await self.wait_start()

    async def kill_container(self):
        msg = 'Killing container {}'.format(self.name)
        self.log(msg, level='debug')
        cmd = '{} kill {}'.format(self.docker_cmd, self.name)
        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')

    async def rm_container(self):
        msg = 'Removing container {}'.format(self.name)
        self.log(msg, level='debug')
        cmd = '{} rm {}'.format(self.docker_cmd, self.name)
        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')

    async def copy2container(self):
        """Recursive copy a directory to the container's src dir."""

        msg = 'Copying files to container {}'.format(self.name)
        self.log(msg, level='debug')
        cmd = 'cd {} && {} cp . {}:{}/{}/'.format(
            self.source_dir, self.docker_cmd, self.name,
            self.container_slave_workdir, self.source_dir)
        self.log(cmd, level='debug')
        await exec_cmd(cmd, cwd='.')

    async def rm_from_container(self):
        """Removes the source code of a container that will not be removed.
        """

        msg = 'Removing files from container {}'.format(self.name)
        self.log(msg, level='debug')
        # removing source dir
        cmd = '{} exec {} rm -rf {}/{}'.format(self.docker_cmd, self.name,
                                               self.container_slave_workdir,
                                               self.source_dir)
        msg = 'Executing {}'.format(cmd)
        self.log(msg, level='debug')
        await exec_cmd(cmd, cwd='.')

        # removing build dir
        cmd = '{} exec {} rm -rf {}/{}-{}'.format(self.docker_cmd, self.name,
                                                  self.container_slave_workdir,
                                                  self.source_dir,
                                                  self.builder_name)
        msg = 'Executing {}'.format(cmd)
        self.log(msg, level='debug')
        await exec_cmd(cmd, cwd='.')

    async def get_container_ip(self):
        # look what a beautiful command!
        msg = 'Getting container ip'
        self.log(msg, level='debug')
        ip_regex = '((1?[0-9][0-9]?|2[0-4][0-9]|25[0-5])\.){3}'
        ip_regex += '(1?[0-9][0-9]?|2[0-4][0-9]|25[0-5])'
        cmd = [self.docker_cmd, 'inspect', self.name, '|', 'grep', '-i',
               'IPAddress', '|', 'grep', '-oE', '-m', '1',
               "'{}'".format(ip_regex)]
        cmd = ' '.join(cmd)
        msg = 'Executing {}'.format(cmd)
        self.log(msg, level='debug')
        r = await exec_cmd(cmd, cwd='.')
        return r

    async def build(self):
        async with self:
            await self.client.build(self.manager.protocol.send_response)
