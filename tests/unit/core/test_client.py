# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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
    async def test_enter(self):

        async def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        await self.client.connect()
        with self.client as client_inst:
            self.assertTrue(client_inst._connected)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    async def test_connect(self):

        async def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        await self.client.connect()
        self.assertTrue(self.client._connected)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    async def test_connect_ssl(self):

        self.has_ssl = False

        async def oc(*a, **kw):
            self.has_ssl = 'ssl' in kw
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        self.client.use_ssl = True
        await self.client.connect()
        self.assertTrue(self.client._connected)
        self.assertTrue(self.has_ssl)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    async def test_connect_ssl_no_validate(self):

        self.ssl_context = None

        async def oc(*a, **kw):
            self.ssl_context = kw.get('ssl')
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        self.client.use_ssl = True
        self.client.validate_cert = False
        await self.client.connect()
        self.assertTrue(self.client._connected)
        self.assertEqual(self.ssl_context.verify_mode, client.ssl.CERT_NONE)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @async_test
    async def test_disconnect(self):

        async def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        await self.client.connect()
        self.client.disconnect()
        self.assertFalse(self.client._connected)

    @async_test
    async def test_write(self):
        self.client.writer = mock.MagicMock(drain=AsyncMagicMock())

        data = {"some": "json"}
        msg = '16\n{"some": "json"}'.encode('utf-8')

        await self.client.write(data)

        called_arg = self.client.writer.write.call_args[0][0].decode()

        self.assertEqual(called_arg, msg.decode())

    @async_test
    async def test_read(self):

        msg = '16\n{"some": "json"}'.encode('utf-8')

        self._rlimit = 0

        async def read(nbytes):
            part = msg[self._rlimit: self._rlimit + nbytes]
            self._rlimit += nbytes
            return part

        self.client.reader = mock.Mock()
        self.client.reader.read = read

        expected = client.OrderedDict({'some': 'json'})
        returned = await self.client.read()

        self.assertEqual(expected, returned)

    @mock.patch.object(client.BaseToxicClient, 'log', mock.Mock())
    @async_test
    async def test_read_with_bad_json(self):

        msg = '19\n{"some": "json"}{sd'.encode('utf-8')

        self._rlimit = 0

        async def read(nbytes):
            part = msg[self._rlimit: self._rlimit + nbytes]
            self._rlimit += nbytes
            return part

        self.client.reader = mock.Mock()
        self.client.reader.read = read

        with self.assertRaises(client.BadJsonData):
            await self.client.read()

    @async_test
    async def test_get_response(self):
        expected = {'code': 0}

        async def read():
            return expected

        self.client.read = read

        response = await self.client.get_response()

        self.assertEqual(response, expected)

    @async_test
    async def test_get_response_with_error(self):

        async def read():
            return {'code': 1,
                    'body': {'error': 'wrong thing!'}}

        self.client.read = read

        with self.assertRaises(client.ToxicClientException):
            await self.client.get_response()

    @async_test
    async def test_request2server(self):
        self.client.write = AsyncMagicMock(spec=self.client.write)
        self.client.read = AsyncMagicMock(
            spec=self.client.read,
            return_value={'body': {'action': 'ok'}})

        r = await self.client.request2server('action', {'the': 'body'},
                                             'token')

        self.assertEqual(r, 'ok')
