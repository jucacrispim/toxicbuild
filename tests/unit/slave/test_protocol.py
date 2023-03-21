# -*- coding: utf-8 -*-

# Copyright 2015-2018, 2023 Juca Crispim <juca@poraodojuca.net>

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
from unittest import mock, TestCase
from unittest.mock import AsyncMock
from toxicbuild.slave import protocols
from tests import async_test


@mock.patch.object(asyncio, 'StreamReader', mock.Mock())
@mock.patch.object(asyncio, 'StreamWriter', mock.MagicMock())
class ProtocolTest(TestCase):

    @mock.patch.object(protocols.BaseToxicProtocol, 'send_response',
                       mock.MagicMock())
    @mock.patch.object(protocols.BaseToxicProtocol, 'get_json_data',
                       mock.MagicMock())
    @mock.patch.object(asyncio, 'StreamReader', mock.MagicMock())
    @mock.patch.object(asyncio, 'StreamWriter', mock.MagicMock())
    def setUp(self):
        super().setUp()
        loop = mock.MagicMock()
        self.protocol = protocols.BuildServerProtocol(loop)
        type(self.protocol)._is_shuting_down = False
        self.transport = mock.Mock()
        # self.protocol.connection_made(transport)
        self.protocol._stream_reader_wr = mock.MagicMock()
        self.protocol._stream_writer = mock.MagicMock()

        self.response = None

        # the return of get_json_data()
        self.message = {'action': 'list_builders',
                        'body': {
                            'repo_id': 'some-id',
                            'repo_url': 'git@bla.com',
                            'branch': 'master',
                            'named_tree': 'v0.1',
                            'vcs_type': 'git',
                            'builder_name': 'bla'}}

        async def w(code, body):
            self.response = {'code': code,
                             'body': body}

        self.protocol.send_response = w

        async def r():
            return self.message

        self.protocol.get_json_data = r

    def test_call(self):
        self.assertEqual(type(self.protocol()), type(self.protocol))

    @async_test
    async def test_healthcheck(self):
        expected = {'code': 0,
                    'body': 'I\'m alive!'}

        self.message = {'action': 'healthcheck', 'token': '123'}

        self.protocol.connection_made(self.transport)
        await self._wait_futures()

        self.assertEqual(expected, self.response)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_get_buildmanager(self):
        self.protocol.data = await self.protocol.get_json_data()
        builder = await self.protocol.get_buildmanager()
        self.assertTrue(builder)

    @async_test
    async def test_get_buildmanager_with_bad_data(self):
        self.protocol.data = await self.protocol.get_json_data()
        del self.protocol.data['body']

        with self.assertRaises(protocols.BadData):
            await self.protocol.get_buildmanager()

    @mock.patch.object(protocols, 'settings', mock.Mock())
    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_build(self):
        protocols.settings.USE_DOCKER = False
        manager = protocols.BuildManager.return_value
        manager.update_and_checkout = AsyncMock()
        manager.build = AsyncMock()
        manager.load_config = AsyncMock()
        self.protocol.data = await self.protocol.get_json_data()
        protocols.BuildManager.return_value.current_build = None

        manager.load_builder = AsyncMock()
        await self.protocol.build()
        self.assertTrue(manager.load_builder.called)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_build_with_bad_data(self):
        self.protocol.data = await self.protocol.get_json_data()
        del self.protocol.data['body']['builder_name']
        manager = protocols.BuildManager.return_value
        manager.load_config = AsyncMock()
        manager.current_build = None
        manager.update_and_checkout = AsyncMock()

        with self.assertRaises(protocols.BadData):
            await self.protocol.build()

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_build_with_bad_builder_config(self):
        manager = protocols.BuildManager.return_value
        manager.update_and_checkout = AsyncMock()
        manager.load_config = AsyncMock()
        manager.load_builder = AsyncMock(
            side_effect=protocols.BadBuilderConfig)
        protocols.BuildManager.return_value.current_build = None
        self.protocol.data = await self.protocol.get_json_data()

        build_info = await self.protocol.build()
        self.assertEqual(build_info['status'], 'exception')

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_list_builders(self):
        expected = {'code': 0,
                    'body': {'builders': ['b1', 'b2']}}

        self.protocol.data = await self.protocol.get_json_data()
        manager = protocols.BuildManager.return_value
        manager.load_config = AsyncMock()

        manager.current_build = None
        manager.update_and_checkout = AsyncMock()
        manager.list_builders.return_value = ['b1', 'b2']

        await self.protocol.list_builders()

        self.assertEqual(self.response, expected)

    @mock.patch.object(protocols, 'log', mock.Mock())
    @async_test
    async def test_client_connected_with_bad_data(self):
        self.message = {"action": "build", 'token': '123'}

        self.protocol.connection_made(self.transport)
        await self._wait_futures()

        self.assertEqual(self.response['code'], 1)

    @mock.patch.object(protocols, 'log', mock.Mock())
    @async_test
    async def test_client_connected_with_exception(self):
        self.message = {"action": "build", 'token': '123'}

        async def build(*a, **kw):
            raise Exception('sauci fufu!')

        self.protocol.build = build

        self.protocol.connection_made(self.transport)
        await self._wait_futures()

        await self.protocol.client_connected()

        self.assertEqual(self.response['code'], 1)

    @async_test
    async def test_client_connected_shutting_down(self):
        type(self.protocol)._is_shuting_down = True
        self.protocol.close_connection = mock.MagicMock(
            spec=self.protocol.close_connection)
        r = await self.protocol.client_connected()
        self.assertTrue(self.protocol.close_connection.called)
        self.assertIsNone(r)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_client_connected_list_builders(self):
        self.message.update({'token': '123'})
        manager = protocols.BuildManager.return_value
        manager.load_config = AsyncMock()
        protocols.BuildManager.return_value.current_build = None

        manager.list_builders.return_value = ['b1', 'b2']
        manager.update_and_checkout = AsyncMock()
        self.protocol.connection_made(self.transport)
        await self._wait_futures()

        self.assertEqual(self.response['body']['builders'], ['b1', 'b2'])

    @async_test
    async def test_client_connected_heathcheck(self):
        self.message = {'action': 'healthcheck', 'token': '123'}

        self.protocol.connection_made(self.transport)
        await self._wait_futures()

        self.assertEqual(self.response['body'], 'I\'m alive!')

    @mock.patch.object(protocols, 'settings', mock.Mock())
    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    async def test_client_connected_build(self):
        protocols.settings.USE_DOCKER = False
        manager = protocols.BuildManager.return_value
        self.message = {'action': 'build',
                        'token': '123',
                        'body': {
                            'repo_id': 'repo_id',
                            'repo_url': 'git@bla.com',
                            'branch': 'master',
                            'named_tree': 'v0.1',
                            'vcs_type': 'git',
                            'builder_name': 'bla'}}
        manager.load_config = AsyncMock()
        manager.current_build = None
        manager.load_builder = AsyncMock()
        manager.update_and_checkout = AsyncMock()
        self.protocol.connection_made(self.transport)
        await self._wait_futures()
        builder = manager.load_builder.return_value
        self.assertTrue(builder.build.called)

    @mock.patch.object(protocols, 'log', mock.Mock())
    @async_test
    async def test_client_connected_with_wrong_action(self):
        self.message = {'action': 'bla', 'token': '123'}

        self.protocol.connection_made(self.transport)

        await self._wait_futures()

        self.assertTrue(self.response['code'], 1)

    async def _wait_futures(self):
        await self.protocol._check_data_future
        total = 10
        i = 0
        while not self.protocol._client_connected_future and i < total:
            i += 1
            await asyncio.sleep(0.5)
        await self.protocol._client_connected_future
