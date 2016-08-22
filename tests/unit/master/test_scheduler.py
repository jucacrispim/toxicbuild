# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest import TestCase
from toxicbuild.master.scheduler import TaskScheduler, scheduler
from tests import async_test


class SchedulerTest(TestCase):

    def setUp(self):
        scheduler.stop()
        super(SchedulerTest, self).setUp()
        self.scheduler = TaskScheduler()
        asyncio.async(self.scheduler.start())

    def tearDown(self):
        self.scheduler.stop()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
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

    def _method2scheduler(self):
        return True

    @asyncio.coroutine
    def _coromethod2scheduler(self):
        return True
