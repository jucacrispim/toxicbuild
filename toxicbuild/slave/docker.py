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
# why the silly DOCKER_WORKDIR settings variable exists - the
# source code to the container instead of creating an image with the source
# code.

# This is odd, but there is a reason for that. The files are
# copied to the container instead of create a container with the files
# because I want to have the option to preserve the environment for future
# builds.


from toxicbuild.core.utils import exec_cmd, LoggerMixin
from toxicbuild.slave import settings


class DockerContainer(LoggerMixin):
    """Class to handle docker containers used to run builds inside it.
    """

    def __init__(self, name, image_name):
        """Constructor for DockerContainer.

        :param name: The name for the container.
        :param image_name: Name of the image that will be used as bas
          to create the container."""

        self.name = name
        self.workdir = settings.DOCKER_WORKDIR
        self.image_name = image_name
        self.docker_cmd = 'docker'

    async def container_exists(self):
        """Checks if a container named as its ``self.name``
        already exists"""

        cmd = '{} container ls --filter name={}'.format(self.docker_cmd,
                                                        self.name)
        cmd += '| wc -l'
        ret = await exec_cmd(cmd, cwd='.')
        return int(ret) > 1

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

    async def copy2container(self, directory):
        """Recursive copy a directory to the container's workdir."""

        msg = 'Copying files to container {}'.format(self.name)
        self.log(msg, level='debug')
        cmd = 'cd {} && {} cp . {}:{}'.format(directory, self.docker_cmd,
                                              self.name,
                                              self.workdir)
        self.log(cmd, level='debug')
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
