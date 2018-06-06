# -*- coding: utf-8 -*-

# Copyright 2015 2016, 2018 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.master import scheduler
from toxicbuild.master.scheduler import (TaskScheduler, SchedulerServer,
                                         UnknownSchedulerAction, Repository,
                                         scheduler_action, asyncio)
from toxicbuild.master.utils import ConsumerTimeout
from tests import async_test, AsyncMagicMock


class SchedulerTest(TestCase):

    def setUp(self):
        scheduler.stop()
        super(SchedulerTest, self).setUp()
        self.scheduler = TaskScheduler()
        self.future = asyncio.async(self.scheduler.start())

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

    @patch.object(scheduler_action, 'consume', AsyncMagicMock())
    @async_test
    async def test_run(self):
        handle = Mock()
        scheduler_action.consume.return_value.aiter_items = ['']

        class Srv(SchedulerServer):

            def handle_request(self, msg):
                self.stop()
                handle()
                return AsyncMagicMock()()

        server = Srv()
        await server.run()
        self.assertTrue(handle.called)

    @patch.object(scheduler_action, 'consume', AsyncMagicMock())
    @async_test
    async def test_run_timeout(self):
        handle = Mock()
        consumer = scheduler_action.consume.return_value

        class Srv(SchedulerServer):

            def handle_request(self, msg):
                self.stop()
                handle()
                return AsyncMagicMock()()

        server = Srv()
        self.t = 0

        async def fm(cancel_on_timeout):
            try:
                if self.t > 0:
                    server.stop()
                else:
                    raise ConsumerTimeout
            finally:
                self.t += 1

            msg = AsyncMagicMock()
            msg.body = {'repo_id': 'some-repo-id'}
            return msg

        consumer.fetch_message = fm
        await server.run()
        self.assertTrue(handle.called)

    @patch.object(asyncio, 'sleep', AsyncMagicMock(spec=asyncio.sleep))
    @async_test
    async def test_shutdown(self):
        self.server._running_tasks = 1

        sleep_mock = AsyncMagicMock()

        async def sleep(t):
            await sleep_mock()
            self.server._running_tasks = 0

        asyncio.sleep = sleep
        await self.server.shutdown()
        self.assertTrue(sleep_mock.called)

    def test_sync_shutdown(self):
        self.server.shutdown = AsyncMagicMock()
        self.server.sync_shutdown()
        self.assertTrue(self.server.shutdown.called)
