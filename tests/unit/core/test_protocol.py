# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
import json
from unittest import mock
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core import protocol


@mock.patch.object(protocol.utils, 'log', mock.MagicMock())
class BaseToxicProtocolTest(AsyncTestCase):

    @mock.patch.object(protocol.utils, 'log', mock.MagicMock())
    def setUp(self):
        super().setUp()
        loop = mock.Mock()
        self.protocol = protocol.BaseToxicProtocol(loop)
        self.protocol._stream_reader = mock.MagicMock()
        self.protocol._stream_writer = mock.MagicMock()

        self.response = None

        def w(msg):
            self.response = json.loads(msg.decode())

        self.protocol._stream_writer.write = w

        # the return of _stream_reader.read()
        self.message = json.dumps(
            {'action': 'thing'}).encode('utf-8')

        @asyncio.coroutine
        def r(limit):
            return self.message

        self.protocol._stream_reader.read = r

    def test_call(self):

        self.assertEqual(self.protocol(), self.protocol)

    @mock.patch.object(protocol.asyncio, 'StreamReader', mock.Mock())
    @mock.patch.object(protocol.asyncio, 'StreamWriter', mock.MagicMock())
    @gen_test
    def test_connection_made(self):
        loop = mock.Mock()
        prot = protocol.BaseToxicProtocol(loop)
        prot._stream_reader = mock.MagicMock()
        prot._stream_writer = mock.MagicMock()
        prot._stream_reader.read = self.protocol._stream_reader.read
        transport = mock.Mock()
        cc_mock = mock.Mock()

        @asyncio.coroutine
        def cc():
            cc_mock()

        prot.client_connected = cc
        prot.connection_made(transport)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
        self.assertTrue(cc_mock.called)

    @gen_test
    def test_check_data_without_data(self):
        self.message = b''

        yield from self.protocol.check_data()

        self.assertEqual(self.response['code'], 1)

    @gen_test
    def test_check_data_without_action(self):
        self.message = b'{"sauci": "fufu"}'

        yield from self.protocol.check_data()
        self.assertEqual(self.response['code'], 1)

    @gen_test
    def test_check_data(self):
        self.message = b'{"action": "hack!"}'

        yield from self.protocol.check_data()

        self.assertEqual(self.protocol.action, 'hack!')

    @gen_test
    def test_send_response(self):
        expected = {'code': 0,
                    'body': 'something!'}

        yield from self.protocol.send_response(code=0, body='something!')

        self.assertEqual(expected, self.response)

    @gen_test
    def test_get_raw_data(self):
        raw = yield from self.protocol.get_raw_data()
        self.assertEqual(raw, self.message)

    @gen_test
    def test_get_json_data(self):
        json_data = yield from self.protocol.get_json_data()

        self.assertEqual(json_data, json.loads(self.message.decode()))

    def test_close_connection(self):
        self.protocol.close_connection()

        self.assertTrue(self.protocol._stream_writer.close.called)
