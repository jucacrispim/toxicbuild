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

from unittest import TestCase
from unittest.mock import Mock, patch
from toxicbuild.master import consumers
from tests import async_test, AsyncMagicMock


class BaseConsumerTest(TestCase):

    def setUp(self):

        handle = Mock()
        self.handle = handle
        self.msg = Mock()
        self.msg.body = {'repo_id': 'someid'}
        self.msg.acknowledge = AsyncMagicMock()
        self.exchange = AsyncMagicMock()
        self.consumer = self.exchange.consume.return_value
        self.consumer.fetch_message.return_value = self.msg

        class Srv(consumers.BaseConsumer):

            def handle_update_request(self, msg):
                self.stop()
                handle()
                return AsyncMagicMock()()

        self.srv_class = Srv

    @async_test
    async def test_run(self):
        server = self.srv_class(self.exchange, lambda: None)
        server.msg_callback = server.handle_update_request
        await server.run()
        self.assertTrue(self.handle.called)

    @async_test
    async def test_run_routing_key(self):
        server = self.srv_class(self.exchange, lambda: None)
        server.msg_callback = server.handle_update_request
        await server.run(routing_key='bla')
        self.assertTrue(self.handle.called)
        kw = self.exchange.consume.call_args[1]
        self.assertIn('routing_key', kw.keys())
        self.assertIn('bla', kw.values())

    @async_test
    async def test_run_timeout(self):
        server = self.srv_class(self.exchange, lambda: None)

        async def fm(cancel_on_timeout=True):
            server.stop()
            raise consumers.ConsumerTimeout

        consumer = self.exchange.consume.return_value
        consumer.fetch_message = fm
        await server.run()
        self.assertFalse(self.handle.called)

    @patch.object(consumers.asyncio, 'sleep', AsyncMagicMock())
    @async_test
    async def test_shutdown(self):

        exchange = AsyncMagicMock()
        server = consumers.BaseConsumer(exchange, lambda: None)
        server._running_tasks = 1
        sleep_mock = Mock()

        def sleep(t):
            sleep_mock()
            server._running_tasks -= 1
            return AsyncMagicMock()()

        consumers.asyncio.sleep = sleep
        await server.shutdown()
        self.assertTrue(sleep_mock.called)

    @patch.object(consumers.BaseConsumer, 'shutdown', AsyncMagicMock(
        spec=consumers.BaseConsumer.shutdown))
    def test_sync_shutdown(self):
        exchange = AsyncMagicMock()
        server = consumers.BaseConsumer(exchange, lambda: None)
        server.sync_shutdown()
        self.assertTrue(server.shutdown.called)
