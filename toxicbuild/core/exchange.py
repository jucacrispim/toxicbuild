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

import json
import asyncamqp
from toxicbuild.core.utils import LoggerMixin


class JsonMessage(asyncamqp.consumer.Message):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = json.loads(self.body.decode())


asyncamqp.consumer.Consumer.MESSAGE_CLASS = JsonMessage


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
    """A simple abstraction for a amqp exchange."""

    def __init__(self, name, exchange_type, connection, durable=False,
                 routing_key=''):
        """Constructor for :class:`~toxicbuid.core.exchange.Exchange`

        :param name: The exchange's name.
        :param exchange_type: The type of the exchange.
        :param connection: An instance of
          :class:`~toxicbuid.core.exchange.AmqpConnection`.
        :param durable: Indicates if wait for the ack from the consumer.
        :param routing_key: A key to route messages to specific consumers.
        """

        self.name = name
        self.queue_name = '{}_queue'.format(self.name)
        self.exchange_type = exchange_type
        self.durable = durable
        self.routing_key = routing_key
        self.connection = connection
        self.transport = None
        self.protocol = None
        self.channel = None
        self.exchange_declared = False
        self.queue_declared = False
        self._store_consume_futures = False
        self._consume_futures = []

    async def declare_and_bind(self):
        """Declares the exchange and queue. Binds the queue to
        to exchange."""

        if not self.connection._connected:
            await self.connection.connect()

        self.channel = await self.connection.protocol.channel()
        self.queue_declared = await self.channel.queue_declare(
            self.queue_name, durable=self.durable)
        self.exchange_declared = await self.channel.exchange_declare(
            self.name, self.exchange_type, durable=self.durable)
        await self.channel.queue_bind(exchange_name=self.name,
                                      queue_name=self.queue_name,
                                      routing_key=self.routing_key)

    async def publish(self, message):
        """Publishes a message to a Rabbitmq exchange

        :param message: The message that will be published in the
          exchange. Must be something that can be serialized into a json"""

        message = json.dumps(message)

        properties = {}

        if self.durable:
            properties['delivery_mode'] = 2

        kw = {'payload': message, 'exchange_name': self.name,
              'properties': properties, 'routing_key': self.routing_key}

        await self.channel.basic_publish(**kw)

    async def consume(self, wait_message=True, timeout=0):
        """Consumes a message from a Rabbitmq queue.

        :param wait_message: Should we wait for new messages in the queue?
        :param timeout: Timeout for waiting messages.
        """

        if self.durable:
            await self.channel.basic_qos(prefetch_count=1, prefetch_size=0,
                                         connection_global=False)

        r = await self.channel.basic_consume(queue_name=self.queue_name,
                                             no_ack=not self.durable,
                                             wait_message=wait_message,
                                             timeout=timeout)
        return r

    async def get_queue_size(self):
        info = await self.channel.queue_declare(self.queue_name,
                                                durable=self.durable,
                                                passive=True,
                                                exclusive=False,
                                                auto_delete=False)
        return int(info['message_count'])
