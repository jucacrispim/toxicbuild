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
        user = MagicMock()

        @asyncio.coroutine
        def _listen(self):
            listen()

        connectors.StreamConnector._listen = _listen
        inst = yield from connectors.StreamConnector._prepare_instance(
            user, 'repo-id', [])
        yield from asyncio.sleep(0)
        self.assertEqual(inst.clients_connected, 1)
        self.assertTrue(listen.called)

    @patch.object(connectors.StreamConnector, '_listen', MagicMock())
    @async_test
    def test_prepare_instance_new_no_id(self):

        listen = MagicMock()
        user = MagicMock()
        user.id = 'some-id'

        @asyncio.coroutine
        def _listen(self):
            listen()

        connectors.StreamConnector._listen = _listen
        inst = yield from connectors.StreamConnector._prepare_instance(user,
                                                                       None,
                                                                       [])
        yield from asyncio.sleep(0)
        self.assertEqual(inst.clients_connected, 1)
        self.assertTrue(listen.called)
        key = ('some-id', connectors.StreamConnector.NONE_REPO_ID,
               ','.join([]))
        self.assertIn(key, connectors.StreamConnector._instances)

    @async_test
    def test_prepare_instance(self):
        repo_id = 'some-repo-id'
        user = MagicMock()
        user.id = 'some-id'
        connector = connectors.StreamConnector(user, repo_id, [])
        connector.clients_connected += 1
        connectors.StreamConnector._instances = {
            (user.id, repo_id, ''): connector}
        inst = yield from connectors.StreamConnector._prepare_instance(user,
                                                                       repo_id,
                                                                       [])
        self.assertIs(inst, connector)
        self.assertEqual(connector.clients_connected, 2)

    def test_release_instance_disconnect(self):
        inst = MagicMock()
        user = MagicMock()
        user.id = 'some-id'
        inst.clients_connected = 1
        event_types = ['build_started', 'build_finished']
        connectors.StreamConnector._instances = {
            ('some-id', 'some-repo', ','.join(event_types)): inst}
        connectors.StreamConnector._release_instance(user, 'some-repo',
                                                     event_types)
        self.assertTrue(inst._disconnect.called)
        self.assertFalse(connectors.StreamConnector._instances)

    def test_release_instance_disconnect_no_id(self):
        inst = MagicMock()
        inst.clients_connected = 1
        user = MagicMock()
        user.id = 'some-id'
        event_types = ['build_started', 'build_finished']
        key = (user.id, connectors.StreamConnector.NONE_REPO_ID, ','.join(
            event_types))
        connectors.StreamConnector._instances = {key: inst}
        connectors.StreamConnector._release_instance(user, None, event_types)
        self.assertTrue(inst._disconnect.called)
        self.assertFalse(connectors.StreamConnector._instances)

    def test_release_instance(self):
        inst = MagicMock()
        inst.clients_connected = 2
        user = MagicMock()
        user.id = 'some-id'
        connectors.StreamConnector._instances = {
            (user.id, 'some-repo', 'build_started,build_finished'): inst}
        event_types = ['build_started', 'build_finished']
        connectors.StreamConnector._release_instance(user, 'some-repo',
                                                     event_types)
        self.assertFalse(inst.disconnect.called)
        self.assertEqual(connectors.StreamConnector._instances[
            (user.id, 'some-repo', 'build_started,build_finished')
        ].clients_connected, 1)

    @patch.object(connectors, 'get_hole_client', MagicMock())
    @async_test
    def test_connect(self):

        user = MagicMock()
        user.id = 'some-id'
        client = MagicMock()

        @asyncio.coroutine
        def get_hole_client(requester, host, port, use_ssl=True,
                            validate_cert=True):
            return client

        connectors.get_hole_client = get_hole_client
        c = connectors.StreamConnector(user, 'http://bla.com/repo.git', [])
        yield from c._connect()
        self.assertTrue(client.connect2stream.called)
        self.assertTrue(c._connected)

    @async_test
    def test_connect_connected(self):
        user = MagicMock()
        user.id = 'some-id'

        c = connectors.StreamConnector(user, 'http://bla.com/repo.git', [])
        c.log = MagicMock()
        c._connected = True
        yield from c._connect()
        self.assertTrue(c.log.called)

    def test_disconnect(self):
        user = MagicMock()
        user.id = 'some-id'

        c = connectors.StreamConnector(user, 'https://ble.net/repo.git', [])
        c.client = MagicMock()
        c._disconnect()
        self.assertTrue(c.client.disconnect.called)
        self.assertFalse(c._connected)

    def test_get_repo_id_with_build(self):
        user = MagicMock()
        user.id = 'some-id'

        c = connectors.StreamConnector(user, 'https://ble.net/repo.git', [])
        body = {'build': {'repository': {'id': 'repo-build-id'}}}
        repo_id = c._get_repo_id(body)
        self.assertEqual(repo_id, 'repo-build-id')

    def test_get_repo_id_with_repo(self):
        user = MagicMock()
        user.id = 'some-id'

        c = connectors.StreamConnector(user, 'https://ble.net/repo.git', [])
        body = {'repository': {'id': 'repo-build-id'}}
        repo_id = c._get_repo_id(body)
        self.assertEqual(repo_id, 'repo-build-id')

    @patch.object(connectors, 'message_arrived', MagicMock())
    @async_test
    def test_listen_bad_data(self):
        user = MagicMock()
        user.id = 'some-id'

        inst = connectors.StreamConnector(user, 'some-repo', [])
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
        user = MagicMock()
        user.id = 'some-id'

        try:
            inst = connectors.StreamConnector(user, 'some-repo', [])
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
    @async_test
    def test_listen_wrong_repo(self):
        user = MagicMock()
        user.id = 'some-id'

        try:
            inst = connectors.StreamConnector(user, 'other-repo', [])
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
            self.assertFalse(connectors.message_arrived.send.called)
        finally:
            delattr(connectors.StreamConnector, '_connected')

    @patch.object(connectors, 'message_arrived', MagicMock())
    @async_test
    def test_listen_wrong_repo_repo_status_changed(self):
        user = MagicMock()
        user.id = 'some-id'

        try:
            inst = connectors.StreamConnector(
                user, connectors.StreamConnector.NONE_REPO_ID, [])
            inst._connect = MagicMock()
            inst.client = MagicMock()

            def _c(self):
                self.index += 1
                return not bool(self.index)

            connectors.StreamConnector._connected = property(_c)

            @asyncio.coroutine
            def get_response():
                return {'body': {'repository': {'id': 'some-repo'},
                                 'event_type': 'repo_status_changed'}}

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
        user = MagicMock()
        user.id = 'some-id'

        repo_id = 'asfd'

        def callback(msg):
            return None

        yield from connectors.StreamConnector.plug(user, repo_id,
                                                   ['some-event', 'other'],
                                                   callback)
        self.assertTrue(connectors.message_arrived.connect.called)
        self.assertTrue(connectors.StreamConnector._prepare_instance.called)

    @patch.object(connectors, 'message_arrived', MagicMock())
    @patch.object(connectors.StreamConnector, '_prepare_instance', MagicMock())
    @async_test
    def test_plug_without_repo_id(self):
        user = MagicMock()
        user.id = 'some-id'

        repo_id = None

        def callback(msg):
            return None

        yield from connectors.StreamConnector.plug(user, repo_id, ['event'],
                                                   callback)
        called_kw = connectors.message_arrived.connect.call_args[1]
        self.assertFalse(called_kw)
        self.assertTrue(connectors.message_arrived.connect.called)

    @patch.object(connectors, 'message_arrived', MagicMock())
    @patch.object(connectors.StreamConnector, '_release_instance', MagicMock())
    def test_unplug(self):
        user = MagicMock()
        user.id = 'some-id'

        repo_id = 'asdf'

        def callback(msg):
            return None

        event_types = ['build_started', 'build_finished']
        connectors.StreamConnector.unplug(user, repo_id, event_types, callback)
        self.assertTrue(connectors.message_arrived.disconnect.called)
        self.assertTrue(connectors.StreamConnector._release_instance.called)
