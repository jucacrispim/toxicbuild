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

from unittest import TestCase

from bson.objectid import ObjectId
from toxicbuild.core.client import BaseToxicClient

from tests import async_test

from . import start_secrets, stop_secrets


def setUpModule():
    start_secrets()


def tearDownModule():
    stop_secrets()


OWNER_ID = ObjectId()


class DummySecretsClient(BaseToxicClient):

    def __init__(self, *args, **kwargs):
        kwargs['use_ssl'] = True
        kwargs['validate_cert'] = False
        super().__init__(*args, **kwargs)
        self.owner = str(OWNER_ID)

    async def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'token': '123'}
        await self.write(data)
        response = await self.get_response()
        return response['body'][action]

    async def add_secret(self):
        action = 'add-secret'
        body = {'owner': self.owner,
                'key': 'something',
                'value': 'very secret'}
        r = await self.request2server(action, body)
        return r

    async def remove_secret(self):
        action = 'remove-secret'
        body = {'owner': self.owner, 'key': 'something'}
        r = await self.request2server(action, body)
        return r

    async def get_secrets(self):
        action = 'get-secrets'
        body = {'owners': [self.owner]}
        r = await self.request2server(action, body)
        return r


class SecretsTest(TestCase):

    @async_test
    async def setUp(self):
        self.client = DummySecretsClient('localhost', 9745)
        await self.client.connect()

    @async_test
    async def tearDown(self):
        self.client.disconnect()

    @async_test
    async def test_01_add_secret(self):
        r = await self.client.add_secret()
        self.assertEqual(r, 'ok')

    @async_test
    async def test_02_get_secrets(self):
        r = await self.client.get_secrets()

        self.assertEqual(len(r), 1)
        self.assertEqual(r[0]['key'], 'something')
        self.assertEqual(r[0]['value'], 'very secret')

    @async_test
    async def test_03_remove_secret(self):
        r = await self.client.remove_secret()
        self.assertEqual(r, 'ok')
