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

# Simple mutex and semaphore using Rabbitmq. As discussed in the
# rabbitmq docs, it is not tolerant with network partitions. Let's see
# how that works for us here.

from aioamqp.exceptions import ChannelClosed
from asyncamqp.exceptions import ConsumerTimeout
from toxicbuild.core.exchange import Exchange
from toxicbuild.core.utils import LoggerMixin


class Lock(LoggerMixin):

    def __init__(self, msg, consumer):
        self.consumer = consumer
        self.msg = msg

    async def __aenter__(self):
        await self.consumer.__aenter__()
        return self

    async def __aexit__(self, exc, exc_type, exc_tb):
        await self.consumer.__aexit__(exc, exc_type, exc_tb)
        await self.reject()

    async def reject(self):
        await self.consumer.channel.basic_cancel(self.envelope.delivery_tag,
                                                 requeue=True)


class Mutex(Exchange):
    """A simple mutex for excluse access to a resource.

    Intended usage:

    .. code-block:: python

        conn = AmqpConnection()
        m = Mutex('mutex-name', conn)
        await m.create()

        async with m.aquire():
            # your stuff here.
    """

    def __init__(self, name, connection):
        super().__init__(name, connection, exchange_type='direct',
                         durable=True, bind_publisher=True,
                         exclusive_consumer_queue=False)

    async def exists(self):
        if self.channel is None:
            self.channel = await self.connection.protocol.channel()
        try:
            await self.channel.queue_declare(
                self.queue_name, durable=self.durable,
                exclusive=self.exclusive_consumer_queue,
                passive=True)
            exists = True
        except ChannelClosed as e:
            if e.code == 404:
                exists = False
            else:
                raise e

            self.channel = None

        return exists

    async def publish_if_not_there(self, msg):
        async with await self.consume(timeout=100) as consumer:
            try:
                is_there = bool(await consumer.fetch_message())
            except ConsumerTimeout:
                is_there = False

        if not is_there:
            await self.publish(msg)

    async def create(self):
        if await self.exists():
            return

        await self.declare()
        msg = {'mutex': True}
        await self.publish_if_not_there(msg)

    async def aquire(self):
        consumer = await self.consume()
        msg = await consumer.fetch_message()
        return Lock(msg, consumer)
