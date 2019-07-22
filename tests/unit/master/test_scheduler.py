# -*- coding: utf-8 -*-

# Copyright 2015 2016, 2018 Juca Crispim <juca@poraodojuca.net>

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


from unittest import TestCase
from unittest.mock import Mock, patch
from toxicbuild.master import scheduler
from toxicbuild.master.scheduler import (TaskScheduler, SchedulerServer,
                                         UnknownSchedulerAction, Repository,
                                         asyncio, BaseConsumer)
from tests import async_test, AsyncMagicMock


class SchedulerTest(TestCase):

    def setUp(self):
        scheduler.stop()
        super(SchedulerTest, self).setUp()
        self.scheduler = TaskScheduler()
        self.future = asyncio.ensure_future(self.scheduler.start())

    def tearDown(self):
        self.scheduler.stop()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(self.future))
        super(SchedulerTest, self).tearDown()

    def test_add_with_call(self):
        def call():
            return True

        self.scheduler.add(call, interval=10)

        self.assertTrue(self.scheduler.tasks[hash(call)])
        task = self.scheduler.tasks[hash(call)]
        self.assertEqual(self.scheduler.consumption_table[task], 0)

    def test_add_with_coro(self):
        @asyncio.coroutine
        def coro():
            return True

        self.scheduler.add(coro, interval=10)

        self.assertTrue(self.scheduler.tasks[hash(coro)])
        task = self.scheduler.tasks[hash(coro)]
        self.assertEqual(self.scheduler.consumption_table[task], 0)

    def test_add_with_method(self):
        self.scheduler.add(self._method2scheduler, interval=10)
        self.assertTrue(self.scheduler.tasks[hash(self._method2scheduler)])

    def test_add_with_coro_method(self):
        self.scheduler.add(self._coromethod2scheduler, interval=10)
        self.assertTrue(self.scheduler.tasks[hash(self._coromethod2scheduler)])

    def test_remove(self):
        def call():
            return True

        self.scheduler.add(call, interval=10)
        self.scheduler.remove(call)

        self.assertFalse(self.scheduler.tasks.get(call))

    @async_test
    async def test_consume_tasks(self):
        self.TASK_CORO_CONSUMED = False
        self.TASK_CALL_CONSUMED = False

        @asyncio.coroutine
        def task_coro():
            self.TASK_CORO_CONSUMED = True

        def task_call():
            self.TASK_CALL_CONSUMED = True

        self.scheduler.add(task_coro, interval=1)
        self.scheduler.add(task_call, interval=1)

        await asyncio.sleep(1.1)

        self.assertTrue(self.TASK_CALL_CONSUMED)
        self.assertTrue(self.TASK_CORO_CONSUMED)

    def _method2scheduler(self):
        return True

    @asyncio.coroutine
    def _coromethod2scheduler(self):
        return True


class SchedulerServerTest(TestCase):

    def setUp(self):
        self.server = SchedulerServer()

    @async_test
    async def test_handle_request_add_update_code(self):
        msg = Mock()
        msg.acknowledge = AsyncMagicMock()
        msg.body = {}
        msg.body['type'] = 'add-update-code'
        self.server.handle_add_update_code = AsyncMagicMock()
        await self.server.handle_request(msg)
        self.assertTrue(self.server.handle_add_update_code.called)

    @async_test
    async def test_handle_request_rm_update_code(self):
        msg = Mock()
        msg.acknowledge = AsyncMagicMock()
        msg.body = {}
        msg.body['type'] = 'rm-update-code'
        self.server.handle_rm_update_code = AsyncMagicMock()
        await self.server.handle_request(msg)
        self.assertTrue(self.server.handle_rm_update_code.called)

    @async_test
    async def test_handle_request_unknown(self):
        msg = Mock()
        msg.acknowledge = AsyncMagicMock()
        msg.body = {}
        msg.body['type'] = 'unknown'
        with self.assertRaises(UnknownSchedulerAction):
            await self.server.handle_request(msg)

    @async_test
    async def test_handle_add_update_request_already_scheduled(self):
        msg = Mock()
        msg.body = {'repository_id': 'some-id'}
        self.server._updates_scheduled.add('some-id')
        r = await self.server.handle_add_update_code(msg)
        self.assertFalse(r)

    @patch.object(Repository, 'objects', AsyncMagicMock())
    @async_test
    async def test_handle_add_update_request_does_not_exist(self, *a, **kw):
        Repository.objects.get.side_effect = Repository.DoesNotExist
        Repository.objects.get.return_value.id = 'id'
        msg = Mock()
        msg.body = {'repository_id': 'some-id'}
        r = await self.server.handle_add_update_code(msg)
        self.assertFalse(r)

    @patch.object(Repository, 'objects', AsyncMagicMock())
    @async_test
    async def test_handle_add_update_request(self, *a, **kw):
        Repository.objects.get.return_value.update_code = lambda: None
        Repository.objects.get.return_value.id = 'id'
        msg = Mock()
        msg.body = {'repository_id': 'some-id'}
        r = await self.server.handle_add_update_code(msg)
        self.assertTrue(r)

    @async_test
    async def test_handle_rm_update_code_not_scheduled(self):
        msg = Mock()
        msg.body = {'repository_id': 'some-id'}
        r = await self.server.handle_rm_update_code(msg)
        self.assertFalse(r)

    @async_test
    async def test_handle_rm_update_code(self):
        msg = Mock()
        msg.body = {'repository_id': 'some-id'}
        self.server._sched_hashes['some-id'] = 'some-hash'
        self.server.scheduler.remove_by_hash = Mock()
        self.server._updates_scheduled.add('some-id')
        r = await self.server.handle_rm_update_code(msg)
        self.assertTrue(r)
        self.assertTrue(self.server.scheduler.remove_by_hash.called)

    @patch.object(BaseConsumer, 'run', AsyncMagicMock())
    @async_test
    async def test_run(self):
        self.server.scheduler.start = AsyncMagicMock()
        server = self.server

        async def run(self, routing_key=None):
            server.stop()

        BaseConsumer.run = run
        await self.server.run()
        self.assertTrue(self.server.scheduler.start.called)
