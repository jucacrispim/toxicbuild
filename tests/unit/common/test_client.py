# -*- coding: utf-8 -*-

# Copyright 2015-2017, 2019 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import MagicMock, patch
from toxicbuild.common.client import (HoleClient, get_hole_client,
                                      ToxicClientException, UserDoesNotExist,
                                      NotEnoughPerms, BadResetPasswordToken,
                                      AlreadyExists)
from tests import async_test, AsyncMagicMock


class HoleClientTest(TestCase):

    @patch.object(HoleClient, 'settings', MagicMock())
    def setUp(self):
        requester = MagicMock()
        requester.id = 'some-id'
        self.client = HoleClient(requester, 'localhost', 7777)

    def test_client_with_token_arg(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = HoleClient(requester, 'localhost', 7777,
                            hole_token='some-token')
        self.assertEqual(client.hole_token, 'some-token')

    @patch.object(HoleClient, 'get_response', AsyncMagicMock())
    @patch.object(HoleClient, 'write', AsyncMagicMock())
    @async_test
    async def test_request2server(self):
        self.client.get_response = AsyncMagicMock(
            return_value={'body': {'action': 'uhu!'}}
        )

        response = await self.client.request2server('action', {})
        called = self.client.write.call_args[0][0]
        self.assertIn('user_id', called.keys())
        self.assertEqual(response, 'uhu!')

    @patch.object(HoleClient, 'get_response', AsyncMagicMock())
    @patch.object(HoleClient, 'write', AsyncMagicMock())
    @async_test
    async def test_request2server_user_authenticate(self):
        self.client.get_response = AsyncMagicMock(
            return_value={'body': {'user-authenticate': 'uhu!'}}
        )

        await self.client.request2server('user-authenticate', {})
        called = self.client.write.call_args[0][0]
        self.assertNotIn('user_id', called.keys())

    @patch.object(HoleClient, 'request2server', AsyncMagicMock())
    @async_test
    async def test_connect2stream(self):
        await self.client.connect2stream({'event_types': []})
        called = self.client.request2server.call_args[0]
        expected = ('stream', {'user_id': 'some-id', 'event_types': []})
        self.assertEqual(called, expected)

    @patch.object(HoleClient, 'request2server', AsyncMagicMock())
    @async_test
    async def test_getattr(self):
        await self.client.test()

        self.assertTrue(self.client.request2server.called)

    @patch.object(HoleClient, 'connect', AsyncMagicMock())
    @async_test
    async def test_get_hole_client(self):
        requester = MagicMock()
        requester.id = 'some-id'
        client = await get_hole_client(requester, 'localhost', 7777,
                                       hole_token='asdf')
        self.assertTrue(client.connect.called)

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'code': '1', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_server_error(self):
        with self.assertRaises(ToxicClientException):
            await self.client.get_response()

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'code': '2', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_user_does_not_exist(self):
        with self.assertRaises(UserDoesNotExist):
            await self.client.get_response()

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'code': '3', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_not_enough_perms(self):
        with self.assertRaises(NotEnoughPerms):
            await self.client.get_response()

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'code': '4', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_bad_reset_token(self):
        with self.assertRaises(BadResetPasswordToken):
            await self.client.get_response()

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'code': '5', 'body': {'error': 'bla'}}))
    @async_test
    async def test_get_response_already_exists(self):
        with self.assertRaises(AlreadyExists):
            await self.client.get_response()

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'code': '0', 'body': {'bla': 'ble'}}))
    @async_test
    async def test_get_response_ok(self):
        r = await self.client.get_response()
        self.assertEqual(r['body']['bla'], 'ble')

    @patch.object(HoleClient, 'read', AsyncMagicMock(
        return_value={'body': {'bla': 'ble'}}))
    @async_test
    async def test_get_response_no_code(self):
        r = await self.client.get_response()
        self.assertEqual(r['body']['bla'], 'ble')
