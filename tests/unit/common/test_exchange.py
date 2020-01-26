# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
import os
from unittest import TestCase
from unittest.mock import patch, Mock
from aioamqp.exceptions import ChannelClosed
from asyncamqp.exceptions import ConsumerTimeout
from toxicbuild.common import exchange
from tests import async_test, AsyncMagicMock


class AmqpConnectionTest(TestCase):

    @patch.object(exchange, 'Lock', Mock(spec=exchange.Lock))
    def setUp(self):
        self.conn = exchange.AmqpConnection()
        self.conn.transport = Mock()
        self.conn.protocol = AsyncMagicMock()
        self.conn.reconn_lock.acquire_write = AsyncMagicMock(
            spec=self.conn.reconn_lock.acquire_write,
            return_value=AsyncMagicMock())

    @patch.object(exchange.asyncamqp, 'connect',
                  AsyncMagicMock(return_value=(AsyncMagicMock(),
                                               AsyncMagicMock())))
    @async_test
    async def test_connect(self):
        await self.conn.connect()
        self.assertTrue(self.conn._connected)

    @async_test
    async def test_disconnect(self):
        await self.conn.disconnect()
        self.assertFalse(self.conn._connected)

    @async_test
    async def test_reconnect_exception(self):
        self.conn.disconnect = AsyncMagicMock(spec=self.conn.disconnect,
                                              side_effect=Exception)
        self.conn.log = Mock(spec=self.conn.log)
        self.conn.connect = AsyncMagicMock(spec=self.conn.connect)
        await self.conn.reconnect()

        self.assertTrue(self.conn.log.called)
        self.assertTrue(self.conn.connect.called)

    @async_test
    async def test_reconnect(self):
        self.conn.disconnect = AsyncMagicMock(spec=self.conn.disconnect)
        self.conn.log = Mock(spec=self.conn.log)
        self.conn.connect = AsyncMagicMock(spec=self.conn.connect)
        await self.conn.reconnect()

        self.assertFalse(self.conn.log.called)
        self.assertTrue(self.conn.connect.called)


class JsonAckMessageTest(TestCase):

    @async_test
    async def test_acknowledge(self):
        b = exchange.json.dumps({}).encode('utf-8')
        channel, envelope, properties = AsyncMagicMock(), Mock(), {}
        msg = exchange.JsonAckMessage(channel, b, envelope, properties)
        msg.channel = AsyncMagicMock()
        await msg.acknowledge()
        self.assertTrue(msg.channel.basic_client_ack.called)

    @async_test
    async def test_reject(self):
        b = exchange.json.dumps({}).encode('utf-8')
        channel, envelope, properties = AsyncMagicMock(), Mock(), {}
        msg = exchange.JsonAckMessage(channel, b, envelope, properties)
        msg.channel = AsyncMagicMock()
        await msg.reject()
        self.assertTrue(msg.channel.basic_reject.called)


class ExchangeTest(TestCase):

    @classmethod
    @patch.object(exchange, 'Lock', Mock(spec=exchange.Lock))
    @async_test
    async def setUpClass(cls):
        host = os.environ.get('AMQPHOST', 'localhost')
        cls.conn = exchange.AmqpConnection(
            **{'host': host, 'port': 5672})
        cls.exchange = None
        await cls.conn.connect()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        try:
            channel = await cls.exchange.connection.protocol.channel()
            await channel.exchange_delete(cls.exchange.name)
        except (ChannelClosed, AttributeError):
            pass
        try:
            await cls.exchange.connection.disconnect()
        except AttributeError:
            pass
        try:
            await cls.conn.disconnect()
        except exchange.AmqpClosedConnection:
            pass

    @async_test
    async def tearDown(self):
        try:
            channel = await self.exchange.connection.protocol.channel()
            await channel.queue_delete(self.exchange.queue_name)
        except (ChannelClosed, AttributeError):
            pass

    @async_test
    async def test_basic_exchange(self):
        msg = {'key': 'value'}

        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=True)
        await type(self).exchange.declare()
        await self.exchange.publish(msg)
        await asyncio.sleep(0.1)
        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 1)
        consumer = await self.exchange.consume(timeout=100)
        async with consumer:
            msg = await consumer.fetch_message()
            await msg.acknowledge()

        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 0)

    @async_test
    async def test_basic_exchange_routing_key(self):
        if self.exchange:
            await self.exchange.connection.disconnect()
        msg = {'key': 'value'}

        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=False,
                                                exclusive_consumer_queue=True)
        await type(self).exchange.declare()

        consumer = await self.exchange.consume(timeout=100,
                                               routing_key='bla')
        await self.exchange.publish(msg, routing_key='bla')
        await self.exchange.publish(msg, routing_key='ble')
        await asyncio.sleep(0.1)

        msg_count = 0

        async with consumer:
            queue_name = consumer.queue_name
            msg = await consumer.fetch_message()
            while msg:
                msg_count += 1
                try:
                    msg = await consumer.fetch_message()
                except ConsumerTimeout:
                    break

        self.assertEqual(msg_count, 1)
        with self.assertRaises(ChannelClosed):
            # It is an exclusive queue, is deleted when consumption is done
            # 404 here
            await self.exchange.get_queue_size(
                queue_name=queue_name)

    @async_test
    async def test_basic_durable_exchange(self):

        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=False)
        await type(self).exchange.declare()

        channel = await self.exchange.connection.protocol.channel()
        await channel.exchange_delete(self.exchange.name)
        await channel.queue_delete(self.exchange.queue_name)
        try:
            self.exchange.durable = True
            old_pchannel = self.exchange.connection.protocol.channel
            self.exchange.connection.protocol.channel = AsyncMagicMock()
            channel = self.exchange.connection.protocol.channel.return_value

            old_channel = self.exchange.channel
            self.exchange.channel = AsyncMagicMock()
            await self.exchange.consume(timeout=100)
            self.assertTrue(channel.basic_qos.called)
        finally:
            self.exchange.channel = old_channel
            self.exchange.connection.protocol.channel = old_pchannel
            await channel.exchange_delete(self.exchange.name)
            await channel.queue_delete(self.exchange.queue_name)
            self.exchange.durable = False
            await self.exchange.declare()
            await channel.close()

    @async_test
    async def test_sequencial_messages(self):
        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=True)
        await type(self).exchange.declare()

        msg = {'key': 'value'}

        await self.exchange.publish(msg)
        await self.exchange.publish(msg)
        await asyncio.sleep(0.1)
        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 2)
        consumer = await self.exchange.consume(timeout=100)
        async with consumer:
            n = 0
            while n < 2:
                n += 1
                message = await consumer.fetch_message()
                self.assertEqual(message.body, msg)
                await message.acknowledge()

        messages_on_queue = await self.exchange.get_queue_size()
        self.assertEqual(messages_on_queue, 0)

    @async_test
    async def test_unbind(self):
        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=True)
        await type(self).exchange.declare(self.exchange.queue_name)

        channel = Mock()
        channel.queue_unbind = AsyncMagicMock()
        channel.close = AsyncMagicMock()
        self.exchange._bound_rt.add('routing-key')
        await self.exchange.unbind('routing-key', channel)
        self.assertTrue(channel.queue_unbind.called)

    @async_test
    async def test_consume_routing_key(self):
        type(self).exchange = exchange.Exchange('test-exc-durable', self.conn,
                                                exchange_type='direct',
                                                durable=True,
                                                bind_publisher=True,
                                                exclusive_consumer_queue=False)
        await self.exchange.declare()
        await self.exchange.publish({'a': 'b'}, routing_key='1')
        consumer = await self.exchange.consume(routing_key='2', timeout=100)
        async with consumer:
            with self.assertRaises(ConsumerTimeout):
                await consumer.fetch_message()

        consumer = await self.exchange.consume(routing_key='1', timeout=100)
        async with consumer:
            msg = await consumer.fetch_message()

        self.assertTrue(msg)

    @async_test
    async def test_queue_delete(self):
        type(self).exchange = exchange.Exchange('test-exc-durable', self.conn,
                                                exchange_type='direct',
                                                durable=True,
                                                bind_publisher=True,
                                                exclusive_consumer_queue=False)

        channel = await self.exchange.connection.protocol.channel()
        queue_name = 'bla'
        self.queue_info = await channel.queue_declare(
            queue_name, durable=False,
            exclusive=False,
            auto_delete=False)

        await self.exchange.queue_delete('bla')

        try:
            await channel.queue_declare(
                queue_name, durable=False,
                exclusive=False,
                passive=True)
            exists = True
        except ChannelClosed:
            exists = False

        self.assertFalse(exists)

    @async_test
    async def test_fetch_message_no_cancel(self):
        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=True)
        await type(self).exchange.declare()
        consumer = await self.exchange.consume(timeout=100)
        consumer.cancel = AsyncMagicMock(spec=consumer.cancel)
        asserted = False
        async with consumer:
            try:
                await consumer.fetch_message(cancel_on_timeout=False)
            except exchange.asyncamqp.exceptions.ConsumerTimeout:
                pass
            asserted = True
            self.assertFalse(consumer.cancel.called)

        self.assertTrue(asserted)

    @async_test
    async def test_fetch_message_no_wait(self):
        type(self).exchange = exchange.Exchange('test-exc', self.conn,
                                                'direct', bind_publisher=True)
        await type(self).exchange.declare()
        consumer = await self.exchange.consume(timeout=100)
        consumer.cancel = AsyncMagicMock(spec=consumer.cancel)
        asserted = False
        consumer.nowait = True
        async with consumer:
            await consumer.fetch_message()
            asserted = True
            self.assertTrue(consumer.cancel.called)

        self.assertTrue(asserted)

    @async_test
    async def test_get_channel(self):
        host = os.environ.get('AMQPHOST', 'localhost')
        self.conn = exchange.AmqpConnection(
            **{'host': host, 'port': 5672})
        await self.conn.connect()
        exch = exchange.Exchange('test-exc', self.conn,
                                 'direct', bind_publisher=True)
        exch.connection.protocol.channel = AsyncMagicMock(
            spec=exch.connection.protocol.channel,
            return_value=Mock())

        r = await exch._get_channel()
        self.assertTrue(r)
        await self.conn.disconnect()

    @async_test
    async def test_get_channel_disconnected(self):
        host = os.environ.get('AMQPHOST', 'localhost')
        self.conn = exchange.AmqpConnection(
            **{'host': host, 'port': 5672})
        await self.conn.connect()

        exch = exchange.Exchange('test-exc', self.conn,
                                 'direct', bind_publisher=True)
        exch.connection.protocol.channel = AsyncMagicMock(
            spec=exch.connection.protocol.channel,
            side_effect=[exchange.AmqpClosedConnection, Mock()])
        exch.connection.reconnect = AsyncMagicMock(
            spec=exch.connection.reconnect)

        r = await exch._get_channel()
        self.assertTrue(r)
        self.assertTrue(exch.connection.reconnect.called)
        await self.conn.disconnect()
