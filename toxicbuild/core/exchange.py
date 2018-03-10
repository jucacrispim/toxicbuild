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

import aioamqp


class Exchange:
    """A simple abstraction for a amqp exchange."""

    def __init__(self, name, exchange_type, durable=False,
                 routing_key='', **conn_kwargs):
        """Constructor for :class:`~toxicbuid.core.exchange.Exchange`

        :param name: The exchange's name.
        :param exchange_type: The type of the exchange.
        :param durable: Indicates if wait for the ack from the consumer.
        :param routing_key: A key to route messages to specific consumers
        :param conn_kwargs: Kwargs used by ``aioamqp.connect()``."""

        self.name = name
        self.queue_name = '{}_queue'.format(self.name)
        self.exchange_type = exchange_type
        self.durable = durable
        self.routing_key = routing_key
        self.conn_kwargs = conn_kwargs
        self.transport = None
        self.protocol = None
        self.channel = None
        self.exchange_declared = False
        self.queue_declared = False

    async def connect(self):
        """Connects to the Rabbitmq server."""

        self.transport, self.protocol = await aioamqp.connect(
            **self.conn_kwargs)

        self.channel = await self.protocol.channel()
        self.queue_declared = await self.channel.queue_declare(
            self.queue_name, durable=self.durable)
        self.exchange_declared = await self.channel.exchange_declare(
            self.name, self.exchange_type, durable=self.durable)
        await self.channel.queue_bind(exchange_name=self.name,
                                      queue_name=self.queue_name,
                                      routing_key=self.routing_key)

    async def disconnect(self):
        """Disconnects from the Rabbitmq server."""

        await self.protocol.close()
        self.transport.close()

    async def publish(self, message):
        """Publishes a message to a Rabbitmq exchange

        :param message: The message that will be published in the
          exchange."""

        properties = {}

        if self.durable:
            properties['delivery_mode'] = 2

        kw = {'payload': message, 'exchange_name': self.name,
              'properties': properties, 'routing_key': self.routing_key}

        await self.channel.publish(**kw)

    async def consume(self, callback):
        """Consumes a message from a Rabbitmq queue."""

        if self.durable:
            self.channel.basic_qos(prefetch_count=1, prefetch_size=0,
                                   connection_global=False)

        await self.channel.basic_consume(callback, queue_name=self.queue_name,
                                         no_ack=not self.durable)
