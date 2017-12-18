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
class DockerContainerBuilderManagerTest(TestCase):

    @patch.object(docker, 'settings', Mock())
    def setUp(self):
        docker.settings.CONTAINER_SLAVE_WORKDIR = 'some/workdir'
        docker.settings.DOCKER_IMAGES = {'linux-generic': 'my-image'}
        manager = Mock()
        platform = 'linux-generic'
        repo_url = 'https://somehere.net/repo.git'
        vcs_type = 'git'
        branch = 'master'
        named_tree = 'asdf'
        builder_name = 'builder-0'
        source_dir = 'source/dir'
        self.container = docker.DockerContainerBuilder(
            manager, platform, repo_url, vcs_type, branch, named_tree,
            builder_name, source_dir)

    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @async_test
    async def test_aenter(self):
        self.container.start_container = AsyncMagicMock()
        self.container.kill_container = AsyncMagicMock()
        self.container.rm_container = AsyncMagicMock()
        self.container.copy2container = AsyncMagicMock()
        async with self.container:
            self.assertTrue(self.container.start_container.called)
            self.assertTrue(self.container.client.__aenter__.called)

    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @async_test
    async def test_aexit(self):
        self.container.start_container = AsyncMagicMock()
        self.container.kill_container = AsyncMagicMock()
        self.container.rm_container = AsyncMagicMock()
        self.container.copy2container = AsyncMagicMock()
        async with self.container:
            pass
        self.assertTrue(self.container.kill_container.called)
        self.assertTrue(self.container.rm_container.called)
        self.assertTrue(self.container.client.__aexit__.called)

    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @async_test
    async def test_aexit_no_remove(self):
        self.container.start_container = AsyncMagicMock()
        self.container.kill_container = AsyncMagicMock()
        self.container.rm_container = AsyncMagicMock()
        self.container.copy2container = AsyncMagicMock()
        self.container.rm_from_container = AsyncMagicMock()
        self.container.remove_env = False
        async with self.container:
            pass
        self.assertTrue(self.container.kill_container.called)
        self.assertFalse(self.container.rm_container.called)
        self.assertTrue(self.container.rm_from_container.called)

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

    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @async_test
    async def test_is_running(self):
        self.container.client.healthcheck = AsyncMagicMock(return_value=True)
        r = await self.container.is_running()
        self.assertTrue(r)

    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock(
        side_effect=Exception))
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @async_test
    async def test_is_running_exception(self):
        self.container.client.healthcheck = AsyncMagicMock(return_value=True)
        r = await self.container.is_running()
        self.assertFalse(r)

    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @patch.object(docker.asyncio, 'sleep', AsyncMagicMock())
    @async_test
    async def test_wait_start(self):
        self.container.client.healthcheck = AsyncMagicMock(
            side_effect=[False, True])
        await self.container.wait_start()
        self.assertTrue(docker.asyncio.sleep.called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_start_container_dont_exists(self):
        self.container.wait_start = AsyncMagicMock()
        self.container.container_exists = AsyncMagicMock(return_value=False)
        expected = 'docker run -t -d --name {} my-image'.format(
            self.container.name)
        await self.container.start_container()
        called = docker.exec_cmd.call_args[0][0]

        self.assertEqual(expected, called)
        self.assertTrue(self.container.wait_start.called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_start_container(self):
        self.container.container_exists = AsyncMagicMock(return_value=True)
        self.container.wait_start = AsyncMagicMock()
        expected = 'docker start {}'.format(self.container.name)
        await self.container.start_container()
        called = docker.exec_cmd.call_args[0][0]

        self.assertEqual(expected, called)
        self.assertTrue(self.container.wait_start.called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_kill_container(self):
        expected = 'docker kill {}'.format(self.container.name)
        await self.container.kill_container()
        called = docker.exec_cmd.call_args[0][0]

        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_copy2container(self):
        expected = 'cd source/dir && docker cp . {}:{}/{}/'.format(
            self.container.name, self.container.container_slave_workdir,
            self.container.source_dir)
        await self.container.copy2container()
        called = docker.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_rm_from_container(self):
        expected_source = 'docker exec {} rm -rf {}/{}'.format(
            self.container.name, self.container.container_slave_workdir,
            self.container.source_dir)

        expected_build = 'docker exec {} rm -rf {}/{}-{}'.format(
            self.container.name, self.container.container_slave_workdir,
            self.container.source_dir, self.container.builder_name)

        await self.container.rm_from_container()
        called_source = docker.exec_cmd.call_args_list[0][0][0]
        called_build = docker.exec_cmd.call_args_list[1][0][0]
        self.assertEqual(expected_source, called_source)
        self.assertEqual(expected_build, called_build)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_rm_container(self):
        expected = 'docker rm {}'.format(self.container.name)
        await self.container.rm_container()
        called = docker.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @patch.object(docker, 'exec_cmd', AsyncMagicMock())
    @async_test
    async def test_get_container_ip(self):
        expected = 'docker inspect {} | grep -i IPAddress '.format(
            self.container.name)
        expected += '| grep -oE -m 1 '
        expected += "'((1?[0-9][0-9]?|2[0-4][0-9]|25[0-5])\.){3}"
        expected += "(1?[0-9][0-9]?|2[0-4][0-9]|25[0-5])'"

        await self.container.get_container_ip()
        called = docker.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @patch.object(docker.ContainerBuildClient, 'build', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aenter__', AsyncMagicMock())
    @patch.object(docker.ContainerBuildClient, '__aexit__', AsyncMagicMock())
    @async_test
    async def test_build(self):
        self.container.start_container = AsyncMagicMock()
        self.container.copy2container = AsyncMagicMock()
        self.container.kill_container = AsyncMagicMock()
        self.container.rm_container = AsyncMagicMock()

        await self.container.build()
        self.assertTrue(self.container.client.build.called)
