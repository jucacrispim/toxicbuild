# -*- coding: utf-8 -*-

# Copyright 2015, 2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest import mock, TestCase
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
        self.transport = mock.Mock()
        # self.protocol.connection_made(transport)
        self.protocol._stream_reader = mock.MagicMock()
        self.protocol._stream_writer = mock.MagicMock()

        self.response = None

        # the return of get_json_data()
        self.message = {'action': 'list_builders',
                        'body': {
                            'repo_url': 'git@bla.com',
                            'branch': 'master',
                            'named_tree': 'v0.1',
                            'vcs_type': 'git',
                            'builder_name': 'bla'}}

        @asyncio.coroutine
        def w(code, body):
            self.response = {'code': code,
                             'body': body}

        self.protocol.send_response = w

        @asyncio.coroutine
        def r():
            return self.message

        self.protocol.get_json_data = r

    def test_call(self):
        self.assertEqual(self.protocol(), self.protocol)

    @async_test
    def test_healthcheck(self):
        expected = {'code': 0,
                    'body': 'I\'m alive!'}

        self.message = {'action': 'healthcheck'}

        self.protocol.connection_made(self.transport)
        yield from self._wait_futures()

        self.assertEqual(expected, self.response)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_get_buildmanager(self):
        self.protocol.data = yield from self.protocol.get_json_data()
        builder = yield from self.protocol.get_buildmanager()
        self.assertTrue(builder)

    @async_test
    def test_get_buildmanager_with_bad_data(self):
        self.protocol.data = yield from self.protocol.get_json_data()
        del self.protocol.data['body']

        with self.assertRaises(protocols.BadData):
            yield from self.protocol.get_buildmanager()

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_build(self):
        self.protocol.data = yield from self.protocol.get_json_data()
        protocols.BuildManager.return_value.current_build = None

        yield from self.protocol.build()

        manager = protocols.BuildManager.return_value.__enter__.return_value
        self.assertTrue(manager.load_builder.called)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_build_with_bad_data(self):
        self.protocol.data = yield from self.protocol.get_json_data()
        del self.protocol.data['body']['builder_name']
        protocols.BuildManager.return_value.current_build = None

        with self.assertRaises(protocols.BadData):
            yield from self.protocol.build()

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_build_with_bad_builder_config(self):
        protocols.BuildManager.return_value.__enter__.return_value.\
            load_builder = mock.Mock(side_effect=protocols.BadBuilderConfig)
        protocols.BuildManager.return_value.current_build = None
        self.protocol.data = yield from self.protocol.get_json_data()

        build_info = yield from self.protocol.build()
        self.assertEqual(build_info['status'], 'exception')

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_list_builders(self):
        expected = {'code': 0,
                    'body': {'builders': ['b1', 'b2']}}

        self.protocol.data = yield from self.protocol.get_json_data()
        protocols.BuildManager.return_value.__enter__.return_value.\
            current_build = None

        manager = protocols.BuildManager.return_value.__enter__.return_value

        manager.list_builders.return_value = ['b1', 'b2']

        yield from self.protocol.list_builders()

        self.assertEqual(self.response, expected)

    @mock.patch.object(protocols, 'log', mock.Mock())
    @async_test
    def test_client_connected_with_bad_data(self):
        self.message = {"action": "build"}

        self.protocol.connection_made(self.transport)
        yield from self._wait_futures()

        self.assertEqual(self.response['code'], 1)

    @mock.patch.object(protocols, 'log', mock.Mock())
    @async_test
    def test_client_connected_with_exception(self):
        self.message = {"action": "build"}

        @asyncio.coroutine
        def build(*a, **kw):
            raise Exception('sauci fufu!')

        self.protocol.build = build

        self.protocol.connection_made(self.transport)
        yield from self._wait_futures()

        yield from self.protocol.client_connected()

        self.assertEqual(self.response['code'], 1)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_client_connected_list_builders(self):

        manager = protocols.BuildManager.return_value.__enter__.return_value
        protocols.BuildManager.return_value.current_build = None

        manager.list_builders.return_value = ['b1', 'b2']

        self.protocol.connection_made(self.transport)
        yield from self._wait_futures()

        self.assertEqual(self.response['body']['builders'], ['b1', 'b2'])

    @async_test
    def test_client_connected_heathcheck(self):
        self.message = {'action': 'healthcheck'}

        self.protocol.connection_made(self.transport)
        yield from self._wait_futures()

        self.assertEqual(self.response['body'], 'I\'m alive!')

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @async_test
    def test_client_connected_build(self):
        self.message = {'action': 'build',
                        'body': {
                            'repo_url': 'git@bla.com',
                            'branch': 'master',
                            'named_tree': 'v0.1',
                            'vcs_type': 'git',
                            'builder_name': 'bla'}}
        protocols.BuildManager.return_value.current_build = None
        self.protocol.connection_made(self.transport)

        yield from self._wait_futures()

        manager = protocols.BuildManager.return_value.__enter__.return_value
        builder = manager.load_builder.return_value

        self.assertTrue(builder.build.called)

    @mock.patch.object(protocols, 'log', mock.Mock())
    @async_test
    def test_client_connected_with_wrong_action(self):
        self.message = {'action': 'bla'}

        self.protocol.connection_made(self.transport)

        yield from self._wait_futures()

        self.assertTrue(self.response['code'], 1)

    @asyncio.coroutine
    def _wait_futures(self):
        yield from self.protocol._check_data_future
        yield from self.protocol._client_connected_future
