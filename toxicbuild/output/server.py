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

from asyncio import ensure_future
from asyncio import get_event_loop
from asyncio import sleep
from asyncamqp.exceptions import ConsumerTimeout
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.output.exchanges import (repo_notifications,
                                         build_notifications)
from toxicbuild.output.notifications import Notification


class OutputMethodServer(LoggerMixin):
    """Fetchs messages from notification queues and dispatches the
    needed output methods."""

    def __init__(self, loop=None):
        self._stop_consuming_messages = False
        self._running_tasks = 0
        self.loop = loop or get_event_loop()

    async def run(self):
        ensure_future(self._handle_build_notifications())
        ensure_future(self._handle_repo_notifications())

    def add_running_task(self):
        self._running_tasks += 1

    def remove_running_task(self):
        self._running_tasks -= 1

    async def _handle_build_notifications(self):
        await self._handle_notifications(build_notifications)

    async def _handle_repo_notifications(self):
        await self._handle_notifications(repo_notifications)

    async def _handle_notifications(self, exchange):
        async with await exchange.consume(timeout=1000) as consumer:
            while not self._stop_consuming_messages:
                try:
                    msg = await consumer.fetch_message(cancel_on_timeout=False)
                except ConsumerTimeout:
                    continue

                self.log('Got msg {} from {}'.format(
                    msg.body['event_type'], msg.body['repository_id']),
                    level='debug')
                ensure_future(self.run_notifications(msg.body))
                await msg.acknowledge()

            self._stop_consuming_messages = False

    async def shutdown(self):
        self._stop_consuming_messages = True
        while self._running_tasks > 0:
            await sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        self.loop.run_until_complete(self.shutdown())

    async def run_notifications(self, msg):
        """Runs all notifications for a given repository that react to a given
        event type.

        :param msg: The incomming message from a notification"""

        repo_id = msg['repository_id']
        event_type = msg['event_type']

        notifications = Notification.get_repo_notifications(repo_id,
                                                            event_type)
        self.log('Running notifications for event_type {}'.format(event_type),
                 level='debug')

        async for notification in notifications:
            self.add_running_task()
            t = ensure_future(notification.run(msg))
            t.add_done_callback(lambda r: self.remove_running_task())
