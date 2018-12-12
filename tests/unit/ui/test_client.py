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
from unittest import TestCase
from unittest.mock import MagicMock, patch
from toxicbuild.ui.client import (UIHoleClient, get_hole_client,
                                  ToxicClientException, UserDoesNotExist,
                                  NotEnoughPerms, BadResetPasswordToken)
from tests import async_test, AsyncMagicMock


class UIHoleClientTest(TestCase):

    def test_client_with_token_arg(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777,
                              hole_token='some-token')
        self.assertEqual(client.hole_token, 'some-token')

    @patch.object(UIHoleClient, 'get_response', MagicMock())
    @patch.object(UIHoleClient, 'write', MagicMock())
    @async_test
    def test_request2server(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        client.get_response = asyncio.coroutine(
            lambda: {'body': {'action': 'uhu!'}})

        response = yield from client.request2server('action', {})
        called = client.write.call_args[0][0]
        self.assertIn('user_id', called.keys())
        self.assertEqual(response, 'uhu!')

    @patch.object(UIHoleClient, 'get_response', MagicMock())
    @patch.object(UIHoleClient, 'write', MagicMock())
    @async_test
    def test_request2server_user_authenticate(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        client.get_response = asyncio.coroutine(
            lambda: {'body': {'user-authenticate': 'uhu!'}})

        yield from client.request2server('user-authenticate', {})
        called = client.write.call_args[0][0]
        self.assertNotIn('user_id', called.keys())

    @patch.object(UIHoleClient, 'request2server', MagicMock())
    @async_test
    def test_connect2stream(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        yield from client.connect2stream({'event_types': []})
        called = client.request2server.call_args[0]
        expected = ('stream', {'user_id': 'some-id', 'event_types': []})
        self.assertEqual(called, expected)

    @patch.object(UIHoleClient, 'request2server', MagicMock())
    @async_test
    def test_getattr(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        yield from client.test()

        self.assertTrue(client.request2server.called)

    @patch.object(UIHoleClient, 'connect', MagicMock())
    @async_test
    def test_get_hole_client(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = yield from get_hole_client(requester, 'localhost', 7777)
        self.assertTrue(client.connect.called)

    @patch.object(UIHoleClient, 'read', AsyncMagicMock(
        return_value={'code': '1', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_server_error(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        with self.assertRaises(ToxicClientException):
            await client.get_response()

    @patch.object(UIHoleClient, 'read', AsyncMagicMock(
        return_value={'code': '2', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_user_does_not_exist(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        with self.assertRaises(UserDoesNotExist):
            await client.get_response()

    @patch.object(UIHoleClient, 'read', AsyncMagicMock(
        return_value={'code': '3', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_not_enough_perms(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        with self.assertRaises(NotEnoughPerms):
            await client.get_response()

    @patch.object(UIHoleClient, 'read', AsyncMagicMock(
        return_value={'code': '4', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_bad_reset_token(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        with self.assertRaises(BadResetPasswordToken):
            await client.get_response()

    @patch.object(UIHoleClient, 'read', AsyncMagicMock(
        return_value={'code': '0', 'body': {'bla': 'ble'}}))
    @async_test
    async def test_get_response_ok(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = UIHoleClient(requester, 'localhost', 7777)
        r = await client.get_response()
        self.assertEqual(r['body']['bla'], 'ble')
