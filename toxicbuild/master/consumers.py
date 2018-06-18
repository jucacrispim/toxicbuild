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
import signal
from asyncamqp.exceptions import ConsumerTimeout
from toxicbuild.core.utils import LoggerMixin


__doc__ = """This module implements consumers for messages published
in exchanges. The consumer react (call something) in response for a
incomming message."""


class BaseConsumer(LoggerMixin):
    """A base class for the consumer that react to incomming messages
    from exchanges"""

    def __init__(self, exchange, msg_callback, loop=None):
        """:param exchange: The exchange in which messages are published
          for the consumer to fetch.
        :param msg_callback: A callable that receives the message"""

        self.exchange = exchange
        self.msg_callback = msg_callback
        self.loop = loop or asyncio.get_event_loop()
        self._stop = False
        self._running_tasks = 0
        signal.signal(signal.SIGTERM, self.sync_shutdown)

    async def run(self, routing_key=None):
        """Starts the consumer.

        :param routing_key: The routing key to consume messages"""

        kw = {'timeout': 1000}
        if routing_key:
            kw['routing_key'] = routing_key

        async with await self.exchange.consume(**kw) as consumer:
            while not self._stop:
                try:
                    msg = await consumer.fetch_message(cancel_on_timeout=False)
                except ConsumerTimeout:
                    continue

                self.log('Consuming message')

                asyncio.ensure_future(self.msg_callback(msg))
                await msg.acknowledge()

            self._stop = False

    def stop(self):
        self._stop = True

    async def shutdown(self):
        self.log('Shutting down')
        self.stop()
        while self._running_tasks > 0:
            self.log('Waiting for tasks')
            await asyncio.sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        self.loop.run_until_complete(self.shutdown())
