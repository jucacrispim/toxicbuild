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
import json
from uuid import uuid4
import asyncamqp
from toxicbuild.core.utils import LoggerMixin


class JsonAckMessage(asyncamqp.consumer.Message):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = json.loads(self.body.decode())

    async def acknowledge(self):
        await self.channel.basic_client_ack(
            delivery_tag=self.envelope.delivery_tag)

    async def reject(self, requeue=True):
        await self.channel.basic_reject(
            self.envelope.delivery_tag, requeue=requeue)


class Consumer(asyncamqp.consumer.Consumer, LoggerMixin):

    async def __aexit__(self, *args, **kwargs):
        await super().__aexit__(*args, **kwargs)
        await self.channel.close()

    async def fetch_message(self, cancel_on_timeout=True):
        if self.nowait and self.queue.empty():
            await self.cancel()
            return None

        elif self.timeout and self.queue.empty():
            t = 0
            while t <= self.timeout:
                await asyncio.sleep(0.001)
                if not self.queue.empty():
                    break
                t += 1
            else:
                if cancel_on_timeout:
                    await self.cancel()
                raise asyncamqp.exceptions.ConsumerTimeout(
                    'Could not get a message in {} ms'.format(self.timeout))

        msg = await self.queue.get()

        self.message = self.MESSAGE_CLASS(*msg)
        return self.message


asyncamqp.channel.Channel.CONSUMER_CLASS = Consumer
asyncamqp.consumer.Consumer.MESSAGE_CLASS = JsonAckMessage


class AmqpConnection(LoggerMixin):
    """A connection for a broker. We can have many channels over
    one connection."""

    def __init__(self, **conn_kwargs):
        """Constructor for AmqpConnection.

        :param conn_kwargs: Kwargs used by ``asyncamqp.connect()``.
        """

        self.conn_kwargs = conn_kwargs
        self.transport = None
        self.protocol = None
        self._connected = False

    async def connect(self):
        """Connects to the Rabbitmq server."""

        self.transport, self.protocol = await asyncamqp.connect(
            **self.conn_kwargs)
        self._connected = True

    async def disconnect(self):
        """Disconnects from the Rabbitmq server."""

        await self.protocol.close()
        self.transport.close()
        self._connected = False


class Exchange(LoggerMixin):
    """A simple abstraction for an amqp exchange.
    """

    def __init__(self, name, connection, exchange_type, durable=False,
                 bind_publisher=True, exclusive_consumer_queue=False):
        """Constructor for :class:`~toxicbuid.core.exchange.Exchange`

        :param name: The exchange's name.
        :param connection: An instance of
          :class:`~toxicbuid.core.exchange.AmqpConnection`.
        :param exchange_type: The type of the exchange.
        :param durable: Indicates if the messages are stored to disk or not.
        :param bind_publisher: If true, a queue will be bound to the
          exchange when publishing stuff. It means that all messages published
          will be sent to a queue when it is published. Otherwise messages
          will be sent to a queue only when a consumer binds a queue to the
          exchange.
        :param exclusive_consumer_queue: Indicates if the consumer queue is
          exclusive to the consumer.
        """

        self.name = name
        self.connection = connection
        self.queue_name = '{}_queue'.format(self.name)
        self.exchange_type = exchange_type
        self.durable = durable
        self.connection = connection
        self.bind_publisher = bind_publisher
        self.transport = None
        self.protocol = None
        self.channel = None
        self.exchange_declared = False
        self.queue_info = None
        self._store_consume_futures = False
        self._consume_futures = []
        self._bound_rt = set()
        self.exclusive_consumer_queue = exclusive_consumer_queue
        self._declared_queues = set()
        self._exclusive_queues = {}

    async def declare(self, queue_name=None):
        """Declares the exchange and queue.

        :param queue_name: The name for the queue to be declared. If None,
           self.queue_name will be used."""

        if not self.connection._connected:
            await self.connection.connect()

        # a default channel, mainly for tests
        # self.channel = await self.connection.protocol.channel()
        # but we use a new channel everytime to avoid waiter already
        # exists stuff.
        channel = await self.connection.protocol.channel()
        try:
            # self.channel = await self.connection.protocol.channel()
            if not queue_name:
                queue_name = self.queue_name

            self.exchange_declared = await channel.exchange_declare(
                self.name, self.exchange_type, durable=self.durable)

            if not self.is_declared(queue_name) and \
               not self.exclusive_consumer_queue:
                await self._declare_queue(queue_name, channel)

        finally:
            await channel.close()

    async def _declare_queue(self, queue_name, channel):

        durable = self.durable and not self.exclusive_consumer_queue
        self.queue_info = await channel.queue_declare(
            queue_name, durable=durable,
            exclusive=self.exclusive_consumer_queue,
            auto_delete=self.exclusive_consumer_queue)
        self._declared_queues.add(queue_name)

    def is_declared(self, queue_name=None):
        return queue_name in self._declared_queues

    def _get_queue_name_for_routing_key(self, routing_key, queue_name=None):
        queue_name = queue_name or self.queue_name

        if routing_key:
            queue_name = '{}-{}'.format(queue_name, routing_key)

        return queue_name

    async def bind(self, routing_key, queue_name=None, channel=None):
        """Binds the queue to the exchange.

        :param routing_key: Routing key to bind the queue.
        :param queue_name: The name of the queue to be bound. If not
          self.queue_name will be used.
        :param channel: Optional channel to use in the communication. A new
          one will be used."""

        if not queue_name:
            queue_name = self.queue_name

        queue_name = self._get_queue_name_for_routing_key(routing_key,
                                                          queue_name)
        local_channel = False
        if not channel:
            channel = await self.connection.protocol.channel()
            local_channel = True

        if not self.is_declared(queue_name):
            await self._declare_queue(queue_name, channel)

        r = await channel.queue_bind(exchange_name=self.name,
                                     queue_name=queue_name,
                                     routing_key=routing_key)

        self._bound_rt.add(routing_key)
        if local_channel:
            await channel.close()
        return r

    async def unbind(self, routing_key, channel=None):
        channel = channel or await self.connection.protocol.channel()
        try:
            r = await channel.queue_unbind(exchange_name=self.name,
                                           queue_name=self.queue_name,
                                           routing_key=routing_key)

            self._bound_rt.remove(routing_key)
        finally:
            await channel.close()
        return r

    async def publish(self, message, routing_key=''):
        """Publishes a message to a Rabbitmq exchange

        :param message: The message that will be published in the
          exchange. Must be something that can be serialized into a json.
        :param routing_key: The routing key to pdublish the message."""

        channel = await self.connection.protocol.channel()
        try:
            if self.bind_publisher:
                await self.bind(routing_key, channel=channel)

            message = json.dumps(message)

            properties = {}

            if self.durable:
                properties['delivery_mode'] = 2

            kw = {'payload': message, 'exchange_name': self.name,
                  'properties': properties, 'routing_key': routing_key}

            await channel.publish(**kw)
        finally:
            await channel.close()

    async def consume(self, wait_message=True, timeout=0,
                      routing_key='', no_ack=False):
        """Consumes a message from a Rabbitmq queue.

        :param wait_message: Should we wait for new messages in the queue?
        :param timeout: Timeout for waiting messages.
        :param no_ack: Indicates if we should send a ack response to the
          server. The ack must be sent by the consumer.
        """

        queue_name = self.queue_name
        channel = await self.connection.protocol.channel()
        if self.exclusive_consumer_queue:
            queue_name = '{}-consumer-queue-{}'.format(self.name, str(uuid4()))
            await self.bind(routing_key, queue_name, channel)
            queue_name = self._get_queue_name_for_routing_key(routing_key,
                                                              queue_name)

        elif routing_key:
            queue_name = self._get_queue_name_for_routing_key(routing_key,
                                                              queue_name)
            await self.bind(routing_key, channel=channel)

        if self.durable:
            await channel.basic_qos(prefetch_count=1, prefetch_size=0,
                                    connection_global=False)

        consumer = await channel.basic_consume(queue_name=queue_name,
                                               no_ack=no_ack,
                                               wait_message=wait_message,
                                               timeout=timeout)
        # help on tests
        consumer.queue_name = queue_name
        return consumer

    async def get_queue_size(self, queue_name=None):
        if not queue_name:
            queue_name = self.queue_name

        channel = await self.connection.protocol.channel()
        try:
            info = await channel.queue_declare(queue_name,
                                               durable=self.durable,
                                               passive=True,
                                               exclusive=False,
                                               auto_delete=False)
        finally:
            await channel.close()

        return int(info['message_count'])

    async def queue_delete(self, queue_name=None):
        """Deletes a queue. If not queue_name, `self.queue_name` will be
        used.

        :param queue_name: The name of the queue to be deleted."""

        queue_name = queue_name or self.queue_name
        try:
            channel = await self.connection.protocol.channel()
            await channel.queue_delete(queue_name)
        finally:
            await channel.close()
