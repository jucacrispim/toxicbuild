# -*- coding: utf-8 -*-

# Copyright 2015, 2018 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from asyncio import ensure_future
import time
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master.consumers import BaseConsumer
from toxicbuild.master.exceptions import UnknownSchedulerAction
from toxicbuild.master.exchanges import scheduler_action
from toxicbuild.master.repository import Repository


__doc__ = """
A very simple implementation of an in memory task scheduler using asyncio.
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


class TaskScheduler(LoggerMixin):

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
            msg = 'Consuming task: {}'.format(repr(task.call_or_coro))
            self.log(msg, level='debug')
            ret = task.call_or_coro()
            if asyncio.coroutines.iscoroutine(ret):
                ensure_future(ret)

    async def start(self):
        if self._started:  # pragma: no cover
            return

        self._started = True

        while not self._stop:
            self.consume_tasks()
            await asyncio.sleep(1)

        self._started = False

    def stop(self):
        self._stop = True


class SchedulerServer(BaseConsumer):
    """Simple server to add or remove something from the scheduler."""

    def __init__(self, loop=None):
        exchange = scheduler_action
        msg_callback = self.handle_request
        super().__init__(exchange, msg_callback)
        self.scheduler = TaskScheduler()
        self._sched_hashes = {}
        self._updates_scheduled = set()

    async def run(self):
        ensure_future(self.scheduler.start())
        self._stop = False
        await super().run()
        self.scheduler.stop()

    async def handle_request(self, msg):
        req_type = msg.body['type']
        self.log('Received {} message'.format(req_type), level='debug')
        self._running_tasks += 1
        try:
            if req_type == 'add-update-code':
                await self.handle_add_update_code(msg)
            elif req_type == 'rm-update-code':
                await self.handle_rm_update_code(msg)
            else:
                raise UnknownSchedulerAction(req_type)
        finally:
            self._running_tasks -= 1

    async def handle_add_update_code(self, msg):
        repo_id = msg.body['repository_id']

        if repo_id in self._updates_scheduled:
            self.log('Update for repo {} already scheduled'.format(repo_id),
                     level='warning')
            return False
        try:
            repo = await Repository.get(id=repo_id)
        except Repository.DoesNotExist:
            self.log('Repository {} DoesNotExist'.format(repo_id),
                     level='error')
            return False
        sched_hash = self.scheduler.add(repo.update_code,
                                        repo.update_seconds)
        self._sched_hashes[str(repo.id)] = sched_hash
        self._updates_scheduled.add(repo_id)
        self.log('add-update-code ok for {}'.format(repo_id))
        return True

    async def handle_rm_update_code(self, msg):
        repo_id = msg.body['repository_id']
        try:
            sched_hash = self._sched_hashes[repo_id]
            self.scheduler.remove_by_hash(sched_hash)
            del self._sched_hashes[repo_id]
            self._updates_scheduled.remove(repo_id)
            r = True
        except KeyError:
            self.log('Update for repo {} not scheduled, can\'t rm.'.format(
                repo_id), level='warning')
            r = False

        return r
