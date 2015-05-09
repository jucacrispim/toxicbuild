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
from toxicbuild.core import client


class BuildClientTest(AsyncTestCase):

    def setUp(self):
        super().setUp()

        addr, port = '127.0.0.1', 7777
        self.client = client.BaseToxicClient(addr, port)

    def test_enter_without_connect(self):
        with self.assertRaises(client.ToxicClientException):
            with self.client as client_inst:
                make_pyflakes_happy = client_inst
                del make_pyflakes_happy

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @gen_test
    def test_enter(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        yield from self.client.connect()
        with self.client as client_inst:
            self.assertTrue(client_inst._connected)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @gen_test
    def test_connect(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        yield from self.client.connect()
        self.assertTrue(self.client._connected)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @gen_test
    def test_disconnect(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        yield from self.client.connect()
        self.client.disconnect()
        self.assertFalse(self.client._connected)

    def test_write(self):
        self.client.writer = mock.Mock()

        data = {'some': 'data'}

        self.client.write(data)

        written_data = self.client.writer.write.call_args[0][0]
        written_data = json.loads(written_data.decode())

        self.assertEqual(written_data, data)

    @gen_test
    def test_read(self):

        @asyncio.coroutine
        def read(nbytes):
            return '{"some": "json"}'.encode('utf-8')

        self.client.reader = mock.Mock()
        self.client.reader.read = read

        expected = {'some': 'json'}
        returned = yield from self.client.read()

        self.assertEqual(expected, returned)

    @gen_test
    def test_get_response(self):
        expected = {'code': 0}

        @asyncio.coroutine
        def read():
            return expected

        self.client.read = read

        response = yield from self.client.get_response()

        self.assertEqual(response, expected)

    @gen_test
    def test_get_response_with_error(self):

        @asyncio.coroutine
        def read():
            return {'code': 1,
                    'body': 'wrong thing!'}

        self.client.read = read

        with self.assertRaises(client.ToxicClientException):
            yield from self.client.get_response()
