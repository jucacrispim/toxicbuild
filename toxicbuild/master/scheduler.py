# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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

import time
import asyncio
try:
    from asyncio import ensure_future
except ImportError:  # pragma: no cover
    from asyncio import async as ensure_future


__doc__ = """
A very simple implementation of a in memory task scheduler using asyncio.
"""


class PeriodicTask:

    """ A task that will be executed in a periodic time interval
    """

    def __init__(self, call_or_coro, interval):
        """:param call_or_coro: coroutine to be consumed at ``interval``.
        :param interval: Time in seconds to consume call_or_coro
        """
        self.call_or_coro = call_or_coro
        self.interval = interval


class TaskScheduler:

    """ A simple scheduler for periodic tasks.
    """

    def __init__(self):
        # self.tasks has the format {hash(task_call_or_coro): task}
        self.tasks = {}

        # self.consumption_table has the format {task: last_consumption}
        self.consumption_table = {}

        self._stop = False
        self._started = False

    def add(self, call_or_coro, interval):
        """ Adds ``call_or_coro`` to be consumed at ``interval``.

        :param call_or_coro: callable or coroutine to be consumed.
        :param interval: time in seconds to consume call_or_coro.
        """

        task = PeriodicTask(call_or_coro, interval)
        cc_hash = hash(call_or_coro)

        self.tasks[cc_hash] = task

        # timestamp 0 for the task to be consumed on firt time
        self.consumption_table[task] = 0.0

        return cc_hash

    def remove(self, call_or_coro):
        """ Removes ``call_or_coro`` from the scheduler
        :param call_or_coro: callable or coroutine to remove
        """
        cc_hash = hash(call_or_coro)
        self.remove_by_hash(cc_hash)

    def remove_by_hash(self, cc_hash):
        """ Removes the callable or couroutine scheduled using ``cc_hash``. """

        task = self.tasks[cc_hash]
        del self.consumption_table[task]
        del self.tasks[cc_hash]

    def consume_tasks(self):
        now = time.time()
        # all tasks that is time to consume again
        tasks2consume = [task for task, t in self.consumption_table.items()
                         if t + task.interval <= now]
        for task in tasks2consume:
            self.consumption_table[task] = now
            ret = task.call_or_coro()
            if asyncio.coroutines.iscoroutine(ret):
                ensure_future(ret)

    @asyncio.coroutine
    def start(self):
        if self._started:  # pragma: no cover
            return

        self._started = True

        while not self._stop:
            self.consume_tasks()
            yield from asyncio.sleep(1)

        self._started = False

    def stop(self):
        self._stop = True
