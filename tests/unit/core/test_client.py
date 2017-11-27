# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core import client
from tests import async_test, AsyncMagicMock


class BuildClientTest(TestCase):

    def setUp(self):
        super().setUp()

        addr, port = '127.0.0.1', 7777
        self.client = client.BaseToxicClient(addr, port)

    def test_enter_without_connect(self):
        with self.assertRaises(client.ToxicClientException):
            with self.client as client_inst:
                make_pyflakes_happy = client_inst
                del make_pyflakes_happy

    @async_test
    async def test_aenter(self):
        self.client.connect = AsyncMagicMock()
        self.client.disconnect = mock.Mock()
        async with self.client:
            self.assertTrue(self.client.connect.called)

    @async_test
    async def test_aexit(self):
        self.client.connect = AsyncMagicMock()
        self.client.disconnect = mock.Mock()
        async with self.client:
            pass

        self.assertTrue(self.client.disconnect.called)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    def test_enter(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        yield from self.client.connect()
        with self.client as client_inst:
            self.assertTrue(client_inst._connected)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    def test_connect(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        yield from self.client.connect()
        self.assertTrue(self.client._connected)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    def test_disconnect(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        yield from self.client.connect()
        self.client.disconnect()
        self.assertFalse(self.client._connected)

    @async_test
    def test_write(self):
        self.client.writer = mock.MagicMock()

        data = {"some": "json"}
        msg = '16\n{"some": "json"}'.encode('utf-8')

        yield from self.client.write(data)

        called_arg = self.client.writer.write.call_args[0][0].decode()

        self.assertEqual(called_arg, msg.decode())

    @async_test
    def test_read(self):

        msg = '16\n{"some": "json"}'.encode('utf-8')

        self._rlimit = 0

        @asyncio.coroutine
        def read(nbytes):
            part = msg[self._rlimit: self._rlimit + nbytes]
            self._rlimit += nbytes
            return part

        self.client.reader = mock.Mock()
        self.client.reader.read = read

        expected = client.OrderedDict({'some': 'json'})
        returned = yield from self.client.read()

        self.assertEqual(expected, returned)

    @mock.patch.object(client.BaseToxicClient, 'log', mock.Mock())
    @async_test
    def test_read_with_bad_json(self):

        msg = '19\n{"some": "json"}{sd'.encode('utf-8')

        self._rlimit = 0

        @asyncio.coroutine
        def read(nbytes):
            part = msg[self._rlimit: self._rlimit + nbytes]
            self._rlimit += nbytes
            return part

        self.client.reader = mock.Mock()
        self.client.reader.read = read

        with self.assertRaises(client.BadJsonData):
            yield from self.client.read()

    @async_test
    def test_get_response(self):
        expected = {'code': 0}

        @asyncio.coroutine
        def read():
            return expected

        self.client.read = read

        response = yield from self.client.get_response()

        self.assertEqual(response, expected)

    @async_test
    def test_get_response_with_error(self):

        @asyncio.coroutine
        def read():
            return {'code': 1,
                    'body': {'error': 'wrong thing!'}}

        self.client.read = read

        with self.assertRaises(client.ToxicClientException):
            yield from self.client.get_response()
