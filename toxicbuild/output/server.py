# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import json
from asyncio import ensure_future
from asyncio import get_event_loop
from asyncio import sleep
from asyncamqp.exceptions import ConsumerTimeout
from pyrocumulus.web.applications import PyroApplication
from pyrocumulus.web.decorators import post, delete, get, put
from pyrocumulus.web.handlers import BasePyroAuthHandler
from pyrocumulus.web.urlmappers import URLSpec
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.output.exchanges import (repo_notifications,
                                         build_notifications)
from toxicbuild.output.notifications import Notification, send_email


class OutputMessageHandler(LoggerMixin):
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
        self.log('Handling notifications', level='debug')
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


class NotificationWebHandler(LoggerMixin, BasePyroAuthHandler):

    """Web handler responsible for listing notification methods and
    enabling/disabling notifications for repositories."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.body = None

    async def async_prepare(self):
        await super().async_prepare()
        if self.request.body:
            self.body = json.loads(self.request.body)

    @post('(.*)')
    async def enable_notification(self, notification_name):
        notification_name = notification_name.decode()
        notification_cls = Notification.get_plugin(notification_name)
        notification = notification_cls(**self.body)
        await notification.save()
        return {notification_name: 'enabled'}

    @delete('(.*)')
    async def disable_notification(self, notification_name):
        notification_name = notification_name.decode()
        notification = await Notification.objects.get(_name=notification_name,
                                                      **self.body)
        await notification.delete()
        return {notification_name: 'disabled'}

    @put('(.*)')
    async def update_notification(self, notification_name):
        notification_name = notification_name.decode()
        repo_id = self.body['repository_id']
        await Notification.objects(
            _name=notification_name, repository_id=repo_id).update_one(
                **self.body)
        return {notification_name: 'updated'}

    @post('send-email')
    async def send_email(self):
        recipients = self.body['recipients']
        subject = self.body['subject']
        message = self.body['subject']
        await send_email(recipients, subject, message)
        return {'send-email': True}

    def _parse_value(self, value):
        if isinstance(value, list):
            value = [str(v) for v in value]
        else:
            value = str(value)

        return value

    def _merge_notif_values(self, schemas, notifs):
        notifs_tb = {n.name: n for n in notifs}
        for schema in schemas:
            try:
                notif = notifs_tb[schema['name']]
            except KeyError:
                continue

            for fname, fconfig in schema.items():
                try:
                    attr = getattr(notif, fname)
                    fconfig['value'] = self._parse_value(attr)
                except TypeError:
                    pass

            schema['enabled'] = True

    @get('list/(.*)')
    async def list_notifications(self, repo_id=None):
        notifications = Notification.list_plugins()
        schemas = [n.get_schema(to_serialize=True) for n in notifications]
        if repo_id:
            repo_id = repo_id.decode()
            notifs = await Notification.objects.filter(
                repository_id=repo_id).to_list()
            self._merge_notif_values(schemas, notifs)
        return {'notifications': schemas}


notification_api = URLSpec('/(.*)', NotificationWebHandler)
app = PyroApplication([notification_api])
