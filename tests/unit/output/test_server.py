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

from bson import ObjectId
from unittest import TestCase
from unittest.mock import patch
from toxicbuild.core.exchange import JsonAckMessage
from toxicbuild.output import server
from toxicbuild.output.exchanges import connect_exchanges, disconnect_exchanges
from toxicbuild.output.notifications import (Notification, SlackNotification)
from tests import async_test, AsyncMagicMock


class OutputMethodServerTest(TestCase):

    @async_test
    async def setUp(self):
        await connect_exchanges()
        self.server = server.OutputMethodServer()
        self.obj_id = ObjectId()
        self.notification = SlackNotification(webhook_url='https://bla.nada',
                                              repository_id=self.obj_id)
        await self.notification.save()

    @patch('aioamqp.protocol.logger')
    @async_test
    async def tearDown(self, *args, **kwargs):
        await disconnect_exchanges()
        await Notification.drop_collection()

    @patch.object(Notification, 'run', AsyncMagicMock(
        spec=Notification.run))
    @async_test
    async def test_run_notifications(self):
        msg = {'repository_id': self.obj_id,
               'event_type': 'buildset-finished'}
        await self.server.run_notifications(msg)
        self.assertTrue(Notification.run.called)

    @patch.object(server, 'repo_notifications', AsyncMagicMock(
        spec=server.repo_notifications))
    @patch.object(server.OutputMethodServer, 'run_notifications',
                  AsyncMagicMock(
                      spec=server.OutputMethodServer.run_notifications))
    @async_test
    async def test_handle_repo_notifications(self):
        msg = AsyncMagicMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'repo-added',
                    'repository_id': self.obj_id}
        consumer = server.repo_notifications.consume.return_value

        async def fm(cancel_on_timeout):
            self.server._stop_consuming_messages = True
            return msg

        consumer.fetch_message = fm

        await self.server._handle_repo_notifications()
        self.assertTrue(self.server.run_notifications.called)

    @patch.object(server, 'repo_notifications', AsyncMagicMock(
        spec=server.repo_notifications))
    @patch.object(server.OutputMethodServer, 'run_notifications',
                  AsyncMagicMock(
                      spec=server.OutputMethodServer.run_notifications))
    @async_test
    async def test_handle_repo_notifications_timeout(self):
        msg = AsyncMagicMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'repo-added',
                    'repository_id': self.obj_id}
        consumer = server.repo_notifications.consume.return_value

        async def fm(cancel_on_timeout):
            self.server._stop_consuming_messages = True
            raise server.ConsumerTimeout

        consumer.fetch_message = fm

        await self.server._handle_repo_notifications()
        self.assertFalse(self.server.run_notifications.called)

    @patch.object(server, 'build_notifications', AsyncMagicMock(
        spec=server.build_notifications))
    @patch.object(server.OutputMethodServer, 'run_notifications',
                  AsyncMagicMock(
                      spec=server.OutputMethodServer.run_notifications))
    @async_test
    async def test_handle_build_notifications(self):
        msg = AsyncMagicMock(spec=JsonAckMessage)
        msg.body = {'event_type': 'build-added',
                    'repository_id': self.obj_id}

        consumer = server.build_notifications.consume.return_value

        async def fm(cancel_on_timeout):
            self.server._stop_consuming_messages = True
            return msg

        consumer.fetch_message = fm

        await self.server._handle_build_notifications()
        self.assertTrue(self.server.run_notifications.called)

    @patch.object(server, 'sleep', AsyncMagicMock())
    @async_test
    async def test_shutdown(self):

        sleep_mock = AsyncMagicMock()

        self.server.add_running_task()

        async def sleep(t):
            self.server.remove_running_task()
            await sleep_mock()

        server.sleep = sleep
        await self.server.shutdown()
        self.assertTrue(sleep_mock.called)

    @async_test
    async def test_run(self):
        self.server._handle_build_notifications = AsyncMagicMock(
            spec=self.server._handle_build_notifications)

        self.server._handle_repo_notifications = AsyncMagicMock(
            spec=self.server._handle_repo_notifications)

        await self.server.run()
        self.assertTrue(self.server._handle_repo_notifications.called)
        self.assertTrue(self.server._handle_build_notifications.called)

    def test_sync_shutdown(self):
        self.server.shutdown = AsyncMagicMock()
        self.server.sync_shutdown()
        self.assertTrue(self.server.shutdown.called)
