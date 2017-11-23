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

from unittest import TestCase
from unittest.mock import patch, Mock
from toxicbuild.slave import docker
from tests import async_test, AsyncMagicMock


@patch.object(docker.LoggerMixin, 'log', Mock())
class DockerContainerManagerTest(TestCase):

    @patch.object(docker, 'settings', Mock())
    def setUp(self):
        self.container = docker.DockerContainer('my-container',
                                                'my-image')

    @patch.object(docker, 'exec_cmd', AsyncMagicMock(return_value='1'))
    @async_test
    async def test_container_exisits_do_not_exist(self):
        exists = await self.container.container_exists()
        self.assertFalse(exists)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock(return_value='2'))
    @async_test
    async def test_container_exisits(self):
        exists = await self.container.container_exists()
        self.assertTrue(exists)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_start_container_dont_exists(self):
        self.container.container_exists = AsyncMagicMock(return_value=False)
        expected = 'docker run -t -d --name my-container my-image'
        await self.container.start_container()
        called = docker.exec_cmd.call_args[0][0]

        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_start_container(self):
        self.container.container_exists = AsyncMagicMock(return_value=True)
        expected = 'docker start my-container'
        await self.container.start_container()
        called = docker.exec_cmd.call_args[0][0]

        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_kill_container(self):
        expected = 'docker kill my-container'
        await self.container.kill_container()
        called = docker.exec_cmd.call_args[0][0]

        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_copy2container(self):
        directory = 'my/dir'
        expected = 'cd my/dir && docker cp . my-container:~/'
        self.container.workdir = '~/'
        await self.container.copy2container(directory)
        called = docker.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_rm_container(self):
        expected = 'docker rm my-container'
        await self.container.rm_container()
        called = docker.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_get_container_ip(self):
        expected = 'docker inspect my-container | grep -i IPAddress '
        expected += '| grep -oE -m 1 '
        expected += "'((1?[0-9][0-9]?|2[0-4][0-9]|25[0-5])\.){3}"
        expected += "(1?[0-9][0-9]?|2[0-4][0-9]|25[0-5])'"

        await self.container.get_container_ip()
        called = docker.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)
