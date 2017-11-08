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

import asyncio
from unittest import TestCase
from unittest.mock import MagicMock, patch
from toxicbuild.ui import connectors
from tests import async_test


class StreamConnectorTest(TestCase):

    def tearDown(self):
        connectors.StreamConnector._instances = {}

    @patch.object(connectors.StreamConnector, '_listen', MagicMock())
    @async_test
    def test_prepare_instance_new(self):

        listen = MagicMock()

        @asyncio.coroutine
        def _listen(self):
            listen()

        connectors.StreamConnector._listen = _listen
        inst = yield from connectors.StreamConnector._prepare_instance(
            'repo-id')
        yield from asyncio.sleep(0)
        self.assertEqual(inst.clients_connected, 1)
        self.assertTrue(listen.called)

    @patch.object(connectors.StreamConnector, '_listen', MagicMock())
    @async_test
    def test_prepare_instance_new_no_id(self):

        listen = MagicMock()

        @asyncio.coroutine
        def _listen(self):
            listen()

        connectors.StreamConnector._listen = _listen
        inst = yield from connectors.StreamConnector._prepare_instance(None)
        yield from asyncio.sleep(0)
        self.assertEqual(inst.clients_connected, 1)
        self.assertTrue(listen.called)
        self.assertIn(connectors.StreamConnector.NONE_REPO_ID,
                      connectors.StreamConnector._instances)

    @async_test
    def test_prepare_instance(self):
        repo_id = 'some-repo-id'
        connector = connectors.StreamConnector(repo_id)
        connector.clients_connected += 1
        connectors.StreamConnector._instances = {repo_id: connector}
        inst = yield from connectors.StreamConnector._prepare_instance(repo_id)
        self.assertIs(inst, connector)
        self.assertEqual(connector.clients_connected, 2)

    def test_release_instance_disconnect(self):
        inst = MagicMock()
        inst.clients_connected = 1
        connectors.StreamConnector._instances = {'some-repo': inst}
        connectors.StreamConnector._release_instance('some-repo')
        self.assertTrue(inst._disconnect.called)
        self.assertFalse(connectors.StreamConnector._instances)

    def test_release_instance_disconnect_no_id(self):
        inst = MagicMock()
        inst.clients_connected = 1
        connectors.StreamConnector._instances = {
            connectors.StreamConnector.NONE_REPO_ID: inst}
        connectors.StreamConnector._release_instance(None)
        self.assertTrue(inst._disconnect.called)
        self.assertFalse(connectors.StreamConnector._instances)

    def test_release_instance(self):
        inst = MagicMock()
        inst.clients_connected = 2
        connectors.StreamConnector._instances = {'some-repo': inst}
        connectors.StreamConnector._release_instance('some-repo')
        self.assertFalse(inst.disconnect.called)
        self.assertEqual(connectors.StreamConnector._instances[
            'some-repo'].clients_connected, 1)

    @patch.object(connectors, 'get_hole_client', MagicMock())
    @async_test
    def test_connect(self):

        client = MagicMock()

        @asyncio.coroutine
        def get_hole_client(host, port):
            return client

        connectors.get_hole_client = get_hole_client
        c = connectors.StreamConnector('http://bla.com/repo.git')
        yield from c._connect()
        self.assertTrue(client.connect2stream.called)
        self.assertTrue(c._connected)

    @async_test
    def test_connect_connected(self):
        c = connectors.StreamConnector('http://bla.com/repo.git')
        c.log = MagicMock()
        c._connected = True
        yield from c._connect()
        self.assertTrue(c.log.called)

    def test_disconnect(self):
        c = connectors.StreamConnector('https://ble.net/repo.git')
        c.client = MagicMock()
        c._disconnect()
        self.assertTrue(c.client.disconnect.called)
        self.assertFalse(c._connected)

    @patch.object(connectors, 'message_arrived', MagicMock())
    @async_test
    def test_listen_bad_data(self):
        inst = connectors.StreamConnector('some-repo')
        inst._connect = MagicMock()
        inst.log = MagicMock()
        inst._connected = True
        inst.client = MagicMock()

        @asyncio.coroutine
        def get_response():
            return {}

        inst.client.get_response = get_response
        yield from inst._listen()
        self.assertFalse(connectors.message_arrived.send.called)

    @patch.object(connectors, 'message_arrived', MagicMock())
    @async_test
    def test_listen(self):
        try:
            inst = connectors.StreamConnector('some-repo')
            inst._connect = MagicMock()
            inst.client = MagicMock()

            def _c(self):
                self.index += 1
                return not bool(self.index)

            connectors.StreamConnector._connected = property(_c)

            @asyncio.coroutine
            def get_response():
                return {'body': {'repository': {'id': 'some-repo'}}}

            inst.client.get_response = get_response
            inst.index = -1
            yield from inst._listen()
            self.assertTrue(connectors.message_arrived.send.called)
        finally:
            delattr(connectors.StreamConnector, '_connected')

    @patch.object(connectors, 'message_arrived', MagicMock())
    @patch.object(connectors.StreamConnector, '_prepare_instance', MagicMock())
    @async_test
    def test_plug(self):
        repo_id = 'asfd'

        def callback(msg): return None

        yield from connectors.StreamConnector.plug(repo_id, callback)
        self.assertTrue(connectors.message_arrived.connect.called)
        self.assertTrue(connectors.StreamConnector._prepare_instance.called)

    @patch.object(connectors, 'message_arrived', MagicMock())
    @patch.object(connectors.StreamConnector, '_prepare_instance', MagicMock())
    @async_test
    def test_plug_without_repo_id(self):
        repo_id = None

        def callback(msg): return None

        yield from connectors.StreamConnector.plug(repo_id, callback)
        called_kw = connectors.message_arrived.connect.call_args[1]
        self.assertFalse(called_kw)
        self.assertTrue(connectors.message_arrived.connect.called)

    @patch.object(connectors, 'message_arrived', MagicMock())
    @patch.object(connectors.StreamConnector, '_release_instance', MagicMock())
    def test_unplug(self):
        repo_id = 'asdf'

        def callback(msg): return None

        connectors.StreamConnector.unplug(repo_id, callback)
        self.assertTrue(connectors.message_arrived.disconnect.called)
        self.assertTrue(connectors.StreamConnector._release_instance.called)
