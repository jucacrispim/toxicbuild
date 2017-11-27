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
from toxicbuild.slave import client
from tests import async_test, AsyncMagicMock


class ContainerBuildClientTest(TestCase):

    def setUp(self):
        container = AsyncMagicMock()
        build_data = {'action': 'build',
                      'token': 'asdf',
                      'body': {'branch': 'master', 'named_tree': 'aslfje',
                               'repo_url': 'http://somerepo.nada/git',
                               'vcs_type': 'git'}}

        container.get_container_ip = AsyncMagicMock(return_value='172.19.0.2')
        self.client = client.ContainerBuildClient(build_data, container)

    @patch.object(client.BaseToxicClient, '__aenter__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, '__aexit__', AsyncMagicMock())
    @patch.object(client, 'settings', Mock())
    @async_test
    async def test_context(self):
        client.settings.CONTAINER_SLAVE_PORT = 1234

        async with self.client:
            base_client = self.client.client
            self.assertTrue(self.client.client.__aenter__.called)

        self.assertTrue(base_client.__aexit__.called)
        self.assertIsNone(self.client.client)

    @patch.object(client, 'settings', Mock())
    @async_test
    async def test_build_without_aenter(self):
        client.settings.CONTAINER_SLAVE_TOKEN = '123'
        outfn = AsyncMagicMock()
        with self.assertRaises(client.NotConnected):
            await self.client.build(outfn)

    @patch.object(client.BaseToxicClient, '__aenter__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, '__aexit__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, 'write', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, 'get_response', AsyncMagicMock(
        side_effect=[{'body': {}, 'code': '0'}, {}]))
    @patch.object(client, 'settings', Mock())
    @async_test
    async def test_build(self):
        client.settings.CONTAINER_SLAVE_PORT = 1234
        outfn = AsyncMagicMock()
        async with self.client:
            await self.client.build(outfn)
            self.assertTrue(outfn.called)

    @patch.object(client, 'settings', Mock())
    @async_test
    async def test_healthcheck_no_client(self):
        client.settings.CONTAINER_SLAVE_PORT = 1234
        with self.assertRaises(client.NotConnected):
            await self.client.healthcheck()

    @patch.object(client, 'settings', Mock())
    @patch.object(client.BaseToxicClient, '__aenter__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, '__aexit__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, 'write', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, 'get_response', AsyncMagicMock(
        return_value={'body': {'I\m alive!'}, 'code': '0'}))
    @async_test
    async def test_heathcheck(self):
        async with self.client:
            ok = await self.client.healthcheck()
        self.assertTrue(ok)

    @patch.object(client, 'settings', Mock())
    @patch.object(client.ContainerBuildClient, 'log', Mock())
    @patch.object(client.BaseToxicClient, '__aenter__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, '__aexit__', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, 'write', AsyncMagicMock())
    @patch.object(client.BaseToxicClient, 'get_response', AsyncMagicMock(
        side_effect=Exception))
    @async_test
    async def test_heathcheck_exception(self):
        async with self.client:
            ok = await self.client.healthcheck()
        self.assertFalse(ok)
