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
    """A simple object to hold while you are doing something, and
    return it when you're done.

    Intended usage:

    .. code-block:: python

        async with Lock(msg, consumer):
            # do your stuff.

    """

    def __init__(self, msg, consumer):
        self.consumer = consumer
        self.msg = msg

    async def __aenter__(self):
        await self.consumer.__aenter__()
        return self

    async def __aexit__(self, exc, exc_type, exc_tb):
        await self.reject()
        await self.consumer.__aexit__(exc, exc_type, exc_tb)

    async def reject(self):
        await self.consumer.channel.basic_reject(
            self.msg.envelope.delivery_tag, requeue=True)


class Mutex(Exchange):
    """A simple mutex for excluse access to a resource.

    Intended usage:

    .. code-block:: python

        conn = AmqpConnection()
        m = Mutex('mutex-name', conn)
        await m.create()

        async with m.acquire():
            # your stuff here.
    """

    def __init__(self, name, connection):
        super().__init__(name, connection, exchange_type='direct',
                         durable=True, bind_publisher=True,
                         exclusive_consumer_queue=False)

    async def exists(self):
        """Checks if the queue for this mutex exists."""

        if not self.connection._connected:
            await self.connection.connect()
            self.channel = None

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

    async def _publish_if_not_there(self, msg):
        """Publishes a message to the queue if there is no message there.

        .. note::

            This is intended to be used by create() at the startup of the
            system. As a simple verification for a race condition that
            my happen when starting more than one instance at the application
            at the sametime. Do NOT use it in any other place. That is not
            really safe."""

        async with await self.consume(timeout=100) as consumer:
            try:
                is_there = bool(await consumer.fetch_message())
            except ConsumerTimeout:
                is_there = False

        if not is_there:
            await self.publish(msg)

    async def create(self):
        """Creates a new queue to the mutex if it does not exist."""

        if await self.exists():
            return

        # Note that we may have a race condition here between the exists()
        # and the declare()
        await self.declare()
        msg = {'mutex': True}
        # that's why we use the _publish_if_not_there
        await self._publish_if_not_there(msg)

    async def acquire(self, routing_key=None, _timeout=None, _wait=True):
        """Acquires the lock. Use it with the async context manager.

        :param routing_key: Routing key of the lock."""
        # _timeout is only for tests
        # _wait for try_acquire
        consumer = await self.consume(routing_key=routing_key,
                                      wait_message=_wait, timeout=_timeout)
        try:
            msg = await consumer.fetch_message()
        except ConsumerTimeout:
            msg = None
        if msg:
            return Lock(msg, consumer)

    async def try_acquire(self, routing_key=None):
        r = await self.acquire(routing_key=routing_key, _timeout=100)
        return r
