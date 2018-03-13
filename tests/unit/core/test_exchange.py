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
from unittest.mock import patch, Mock
from toxicbuild.core import exchange
from tests import async_test, AsyncMagicMock


class AmqpConnectionTest(TestCase):

    @patch.object(exchange.asyncamqp, 'connect',
                  AsyncMagicMock(return_value=(AsyncMagicMock(),
                                               AsyncMagicMock())))
    @async_test
    async def test_connect(self):
        conn = exchange.AmqpConnection()
        await conn.connect()
        self.assertTrue(conn._connected)

    @async_test
    async def test_disconnect(self):
        conn = exchange.AmqpConnection()
        conn.transport = Mock()
        conn.protocol = AsyncMagicMock()
        await conn.disconnect()
        self.assertFalse(conn._connected)


class ExchangeTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.conn = exchange.AmqpConnection(
            **{'host': 'localhost', 'port': 5672})
        cls.exchange = exchange.Exchange('test_exchange',
                                         exchange_type='direct',
                                         connection=cls.conn)
        await cls.exchange.declare_and_bind()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await cls.exchange.channel.exchange_delete(cls.exchange.name)
        await cls.exchange.channel.queue_delete(cls.exchange.queue_name)
        await cls.exchange.connection.disconnect()

    @async_test
    async def test_basic_exchange(self):
        msg = {'key': 'value'}

        await self.exchange.publish(msg)
        await asyncio.sleep(0.1)
        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 1)
        consumer = await self.exchange.consume(timeout=100)
        async with consumer:
            await consumer.fetch_message()

        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 0)

    @async_test
    async def test_basic_durable_exchange(self):

        await self.exchange.channel.exchange_delete(self.exchange.name)
        await self.exchange.channel.queue_delete(self.exchange.queue_name)

        try:
            self.exchange.durable = True
            old_channel = self.exchange.channel
            self.exchange.channel = AsyncMagicMock()
            await self.exchange.consume(timeout=100)
            self.assertTrue(self.exchange.channel.basic_qos.called)
        finally:
            self.exchange.channel = old_channel
            await self.exchange.channel.exchange_delete(self.exchange.name)
            await self.exchange.channel.queue_delete(self.exchange.queue_name)
            self.exchange.durable = False
            await self.exchange.declare_and_bind()

    @async_test
    async def test_sequencial_messages(self):
        msg = {'key': 'value'}

        await self.exchange.publish(msg)
        await self.exchange.publish(msg)
        await asyncio.sleep(0.1)
        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 2)
        consumer = await self.exchange.consume(wait_message=False)
        async with consumer:
            async for message in consumer:
                self.assertEqual(message.body, msg)

        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 0)
