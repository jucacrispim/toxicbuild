# -*- coding: utf-8 -*-

import asyncio
import json
import mock
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.slave import protocols, build


@mock.patch.object(protocols.utils, 'log', mock.MagicMock())
class ProtocolTest(AsyncTestCase):
    @mock.patch.object(protocols.asyncio, 'StreamReader', mock.MagicMock())
    @mock.patch.object(protocols.asyncio, 'StreamWriter', mock.MagicMock())
    @mock.patch.object(protocols.utils, 'log', mock.MagicMock())
    def setUp(self):
        super().setUp()
        loop = mock.MagicMock()
        transport = mock.MagicMock()
        self.protocol = protocols.BuildServerProtocol(loop)
        self.protocol.connection_made(transport)

        self.response = None

        # the return of _stream_reader.read()
        self.message = json.dumps(
            {'action': 'list_builders',
             'body': {
                 'repo_url': 'git@bla.com',
                 'branch': 'master',
                 'named_tree': 'v0.1',
                 'vcs_type': 'git',
                 'builder_name': 'bla'}}).encode('utf-8')

        def w(msg):
            self.response = json.loads(msg.decode())

        self.protocol._stream_writer.write = w

        @asyncio.coroutine
        def r(limit):
            return self.message

        self.protocol._stream_reader.read = r

    def test_call(self):
        self.assertEqual(self.protocol(), self.protocol)

    @gen_test
    def test_send_response(self):
        expected = {'code': 0,
                    'body': 'something!'}

        yield from self.protocol.send_response(code=0, body='something!')

        self.assertEqual(expected, self.response)

    @gen_test
    def test_healthcheck(self):
        expected = {'code': 0,
                    'body': 'I\'m alive!'}

        yield from self.protocol.healthcheck()

        self.assertEqual(expected, self.response)

    @gen_test
    def test_get_raw_data(self):
        raw = yield from self.protocol.get_raw_data()
        self.assertEqual(raw, self.message)

    @gen_test
    def test_get_json_data(self):
        self.protocol.raw_data = yield from self.protocol.get_raw_data()
        json_data = self.protocol.get_json_data()

        self.assertEqual(json_data, json.loads(self.message.decode()))

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @gen_test
    def test_get_buildmanager(self):
        self.protocol.raw_data = yield from self.protocol.get_raw_data()
        self.protocol.data = self.protocol.get_json_data()

        builder = yield from self.protocol.get_buildmanager()
        self.assertTrue(builder.update_and_checkout.called)

    @gen_test
    def test_get_buildmanager_with_bad_data(self):
        self.protocol.raw_data = yield from self.protocol.get_raw_data()
        self.protocol.data = self.protocol.get_json_data()
        del self.protocol.data['body']

        with self.assertRaises(protocols.BadData):
            builder = yield from self.protocol.get_buildmanager()

    def test_close_connection(self):
        self.protocol.close_connection()

        self.assertTrue(self.protocol._stream_writer.close.called)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @gen_test
    def test_build(self):
        self.protocol.raw_data = yield from self.protocol.get_raw_data()
        self.protocol.data = self.protocol.get_json_data()

        yield from self.protocol.build()

        manager = protocols.BuildManager.return_value
        self.assertTrue(manager.load_builder.called)

    @gen_test
    def test_build_with_bad_data(self):
        self.protocol.raw_data = yield from self.protocol.get_raw_data()
        self.protocol.data = self.protocol.get_json_data()
        del self.protocol.data['body']

        with self.assertRaises(protocols.BadData):
            yield from self.protocol.build()

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @gen_test
    def test_list_builders(self):
        expected = {'code': 0,
                    'body': {'builders': ['b1', 'b2']}}

        self.protocol.raw_data = yield from self.protocol.get_raw_data()
        self.protocol.data = self.protocol.get_json_data()

        manager = protocols.BuildManager.return_value

        manager.list_builders.return_value = ['b1', 'b2']

        yield from self.protocol.list_builders()

        self.assertEqual(self.response, expected)

    @gen_test
    def test_client_connected_without_data(self):
        self.message = b''

        yield from self.protocol.client_connected()

        self.assertEqual(self.response['code'], 1)

    @gen_test
    def test_client_connected_with_bad_data(self):
        self.message = b'{"action": "build"}'

        yield from self.protocol.client_connected()

        self.assertEqual(self.response['code'], 1)

    @gen_test
    def test_client_connected_with_exception(self):
        self.message = b'{"action": "build"}'

        @asyncio.coroutine
        def build(*a, **kw):
            raise Exception('sauci fufu!')

        self.protocol.build = build

        yield from self.protocol.client_connected()

        self.assertEqual(self.response['code'], 1)

    @gen_test
    def test_client_connected_without_action(self):
        self.message = b'{"notaction": "bla"}'

        yield from self.protocol.client_connected()

        self.assertEqual(self.response['code'], 1)

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @gen_test
    def test_client_connected_list_builders(self):
        manager = protocols.BuildManager.return_value

        manager.list_builders.return_value = ['b1', 'b2']
        yield from self.protocol.client_connected()

        self.assertEqual(self.response['body']['builders'], ['b1', 'b2'])

    @gen_test
    def test_client_connected_heathcheck(self):
        self.message = json.dumps(
            {'action': 'healthcheck'}
        ).encode('utf-8')

        yield from self.protocol.client_connected()
        self.assertEqual(self.response['body'], 'I\'m alive!')

    @mock.patch.object(protocols, 'BuildManager',
                       mock.MagicMock(spec=protocols.BuildManager))
    @gen_test
    def test_client_connected_build(self):
        self.message = json.dumps(
            {'action': 'build',
             'body': {
                 'repo_url': 'git@bla.com',
                 'branch': 'master',
                 'named_tree': 'v0.1',
                 'vcs_type': 'git',
                 'builder_name': 'bla'}}).encode('utf-8')

        yield from self.protocol.client_connected()

        manager = protocols.BuildManager.return_value

        builder = manager.load_builder.return_value

        self.assertTrue(builder.build.called)
