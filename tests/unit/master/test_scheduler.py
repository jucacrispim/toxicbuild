# -*- coding: utf-8 -*-

import asyncio
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.master import scheduler


class SchedulerTest(AsyncTestCase):
    def setUp(self):
        super(SchedulerTest, self).setUp()
        self.scheduler = scheduler.TaskScheduler()
        asyncio.async(self.scheduler.start())

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def tearDown(self):
        self.scheduler.stop()
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

    def test_remove(self):
        def call():
            return True

        self.scheduler.add(call, interval=10)
        self.scheduler.remove(call)

        self.assertFalse(self.scheduler.tasks.get(call))

    @gen_test
    def test_consume_tasks(self):
        self.TASK_CORO_CONSUMED = False
        self.TASK_CALL_CONSUMED = False

        @asyncio.coroutine
        def task_coro():
            self.TASK_CORO_CONSUMED = True

        def task_call():
            self.TASK_CALL_CONSUMED = True


        self.scheduler.add(task_coro, interval=1)
        self.scheduler.add(task_call, interval=1)

        yield from asyncio.sleep(1.1)

        self.assertTrue(self.TASK_CALL_CONSUMED)
        self.assertTrue(self.TASK_CORO_CONSUMED)
