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
import json
from unittest import TestCase
from toxicbuild.core import exchange
from tests import async_test


class ExchangeTest(TestCase):

    @async_test
    async def setUp(self):
        self.conn_kw = {'host': 'localhost', 'port': 5672}
        self.exchange = exchange.Exchange('test_exchange',
                                          'direct',  **self.conn_kw)
        await self.exchange.connect()

    @async_test
    async def tearDown(self):
        await self.exchange.channel.exchange_delete(self.exchange.name)
        await self.exchange.channel.queue_delete(self.exchange.queue_name)
        await self.exchange.disconnect()

    @async_test
    async def test_basic_exchange(self):
        self.CONSUMED = False

        async def cb(channel, body, envelop, properties):
            self.CONSUMED = True

        msg = json.dumps({'key': 'value'})
        await self.exchange.publish(msg)
        await self.exchange.consume(cb)
        await asyncio.sleep(0.1)
        self.assertTrue(self.CONSUMED)

    @async_test
    async def test_basic_durable_exchange(self):

        await self.exchange.channel.exchange_delete(self.exchange.name)
        await self.exchange.channel.queue_delete(self.exchange.queue_name)

        self.CONSUMED = False

        async def cb(channel, body, envelope, properties):
            self.CONSUMED = True
            self.exchange.channel.basic_client_ack(
                delivery_tag=envelope.delivery_tag)

        msg = json.dumps({'key': 'value'})
        await self.exchange.disconnect()
        self.exchange.durable = True
        await self.exchange.connect()
        await self.exchange.publish(msg)
        await self.exchange.consume(cb)
        await asyncio.sleep(0.1)
        self.assertTrue(self.CONSUMED)
