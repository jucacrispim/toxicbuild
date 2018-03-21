# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.core import coordination
from toxicbuild.core.exchange import AmqpConnection
from tests import async_test, AsyncMagicMock


class MutexTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.conn = AmqpConnection(**{'host': 'localhost',
                                     'port': 5672})
        await cls.conn.connect()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await cls.conn.disconnect()

    def setUp(self):
        self.mutex = coordination.Mutex('test-mutex', self.conn)

    @async_test
    async def tearDown(self):
        if self.mutex.channel:
            self.mutex.channel.basic_cancel(self.mutex.queue_name)
            await self.mutex.channel.queue_delete(self.mutex.queue_name)
            await self.mutex.channel.close()

    @async_test
    async def test_exists_doesnt_exit(self):
        r = await self.mutex.exists()
        self.assertFalse(r)

    @async_test
    async def test_exists(self):
        await self.mutex.declare()
        r = await self.mutex.exists()
        self.assertTrue(r)

    @async_test
    async def test_publish_if_not_there_already_there(self):
        await self.mutex.declare()
        await self.mutex.publish({})
        await asyncio.sleep(0.1)
        self.mutex.publish = AsyncMagicMock()
        await self.mutex.publish_if_not_there({})
        self.assertFalse(self.mutex.publish.called)

    @async_test
    async def test_publish_if_not_there(self):
        await self.mutex.declare()
        self.mutex.publish = AsyncMagicMock()
        await self.mutex.publish_if_not_there({})
        self.assertTrue(self.mutex.publish.called)

    @async_test
    async def test_create_already_exists(self):
        self.mutex.exists = AsyncMagicMock(return_value=True)
        self.mutex.declare = AsyncMagicMock()
        await self.mutex.create()
        self.assertFalse(self.mutex.declare.called)

    @async_test
    async def test_create(self):
        self.mutex.exists = AsyncMagicMock(return_value=False)
        self.mutex.declare = AsyncMagicMock()
        self.mutex.publish_if_not_there = AsyncMagicMock()
        await self.mutex.create()
        self.assertTrue(self.mutex.declare.called)
        self.assertTrue(self.mutex.publish_if_not_there.called)
