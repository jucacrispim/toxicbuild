# -*- coding: utf-8 -*-
# Copyright 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import logging
from unittest import TestCase
from unittest.mock import Mock, patch, AsyncMock

from bson.objectid import ObjectId

from tests import async_test
from toxicbuild.secrets import server


class SecretsProtocolTest(TestCase):

    def setUp(self):
        self.protocol = server.SecretsProtocol(Mock())

    @async_test
    async def tearDown(self):
        await server.Secret.drop_collection()

    @async_test
    async def test_client_connected_bad_action(self):
        self.protocol.action = 'bad'

        with self.assertRaises(AssertionError):
            await self.protocol.client_connected()

    @patch.object(server.SecretsProtocol, 'send_response', AsyncMock(
        spec=server.SecretsProtocol.send_response))
    @async_test
    async def test_client_connected_action_error(self):
        logging.disable(logging.CRITICAL)
        self.protocol.action = 'add-secret'

        try:
            r = await self.protocol.client_connected()

            self.assertTrue(self.protocol.send_response.called)
            self.assertIs(r, False)
        finally:
            logging.disable(logging.NOTSET)

    @patch.object(server.SecretsProtocol, 'send_response', AsyncMock(
        spec=server.SecretsProtocol.send_response))
    @async_test
    async def test_add_or_update_secret_new_secret(self):
        self.protocol.action = 'add-or-update-secret'
        self.protocol.data = {}
        self.protocol.data['body'] = {'owner': str(ObjectId()),
                                      'key': 'something',
                                      'value': 'very secret'}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        s = await server.Secret.objects.get(key='something')
        self.assertNotEqual(s.value, 'very secret')

    @patch.object(server.SecretsProtocol, 'send_response', AsyncMock(
        spec=server.SecretsProtocol.send_response))
    @async_test
    async def test_add_or_update_secret_update_secret(self):
        self.protocol.action = 'add-or-update-secret'
        self.protocol.data = {}
        self.protocol.data['body'] = {'owner': str(ObjectId()),
                                      'key': 'something',
                                      'value': 'very secret'}
        await self.protocol.client_connected()

        self.protocol.data['body']['value'] = 'other secret'

        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        s = await server.Secret.objects.get(key='something')
        plain = s.to_dict()['value']
        self.assertEqual(plain, 'other secret')

    @patch.object(server.SecretsProtocol, 'send_response', AsyncMock(
        spec=server.SecretsProtocol.send_response))
    @async_test
    async def test_get_secrets(self):
        owner = str(ObjectId())
        await server.Secret.add(owner, 'something', 'very secret')
        self.protocol.action = 'get-secrets'
        self.protocol.data = {}
        self.protocol.data['body'] = {'owners': [owner]}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        s = self.protocol.send_response.call_args[1]['body'][
            'get-secrets'][0]['value']
        self.assertEqual(s, 'very secret')

    @patch.object(server.SecretsProtocol, 'send_response', AsyncMock(
        spec=server.SecretsProtocol.send_response))
    @async_test
    async def test_remove_secret(self):
        owner = str(ObjectId())
        await server.Secret.add(owner, 'something', 'very secret')
        self.protocol.action = 'remove-secret'
        self.protocol.data = {}
        self.protocol.data['body'] = {'owner': owner,
                                      'key': 'something'}
        r = await self.protocol.client_connected()

        assert self.protocol.send_response.called
        assert r is True

        c = await server.Secret.objects.count()
        self.assertEqual(c, 0)
