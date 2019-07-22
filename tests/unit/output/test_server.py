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

from bson import ObjectId
from unittest import TestCase
from unittest.mock import patch, MagicMock
from toxicbuild.core.exchange import JsonAckMessage
from toxicbuild.output import server
from toxicbuild.output.exchanges import connect_exchanges, disconnect_exchanges
from toxicbuild.output.notifications import (Notification, SlackNotification)
from tests import async_test, AsyncMagicMock


class OutputMessageHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        await connect_exchanges()
        self.server = server.OutputMessageHandler()
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
    @patch.object(server.OutputMessageHandler, 'run_notifications',
                  AsyncMagicMock(
                      spec=server.OutputMessageHandler.run_notifications))
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
    @patch.object(server.OutputMessageHandler, 'run_notifications',
                  AsyncMagicMock(
                      spec=server.OutputMessageHandler.run_notifications))
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
    @patch.object(server.OutputMessageHandler, 'run_notifications',
                  AsyncMagicMock(
                      spec=server.OutputMessageHandler.run_notifications))
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


class NotificationWebHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        request = MagicMock()
        request.cookies = {}
        application = MagicMock()
        self.handler = server.NotificationWebHandler(application,
                                                     request=request)

    @async_test
    async def tearDown(self):
        await server.Notification.drop_collection()

    @patch.object(server.BasePyroAuthHandler, 'async_prepare',
                  AsyncMagicMock())
    @async_test
    async def test_async_prepare(self):
        self.handler.request.body = '{"some": "thing"}'
        await self.handler.async_prepare()
        self.assertTrue(self.handler.body['some'])

    @patch.object(server.BasePyroAuthHandler, 'async_prepare',
                  AsyncMagicMock())
    @async_test
    async def test_async_prepare_no_body(self):
        self.handler.request.body = None
        await self.handler.async_prepare()
        self.assertIsNone(self.handler.body)

    @async_test
    async def test_enable_notification(self):
        obj_id = ObjectId()
        self.handler.body = {'repository_id': str(obj_id),
                             'webhook_url': 'https://bla.nada'}
        await self.handler.enable_notification(b'custom-webhook')
        qs = Notification.objects.filter(repository_id=str(obj_id))
        count = await qs.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_disable_notification(self):
        obj_id = ObjectId()
        self.handler.body = {'repository_id': str(obj_id),
                             'webhook_url': 'https://bla.nada'}
        await self.handler.enable_notification(b'custom-webhook')

        self.handler.body = {'repository_id': str(obj_id)}
        await self.handler.disable_notification(b'custom-webhook')
        qs = Notification.objects.filter(repository_id=str(obj_id))
        count = await qs.count()
        self.assertEqual(count, 0)

    @async_test
    async def test_list_notifications(self):
        notif = (await self.handler.list_notifications())['notifications']
        self.assertTrue(notif[0]['name'])
        self.assertEqual(len(notif), 3, [n['name'] for n in notif])

    @async_test
    async def test_list_notifications_repo_id(self):
        obj_id = ObjectId()
        slack_notif = SlackNotification(webhook_url='https://bla.nada',
                                        repository_id=obj_id,
                                        statuses=['success', 'fail'])
        await slack_notif.save()

        notif = (await self.handler.list_notifications(
            bytes(str(obj_id), encoding='utf-8')))['notifications']
        for schema in notif:
            if schema['name'] == 'slack-notification':
                self.assertEqual(schema['webhook_url']['value'],
                                 'https://bla.nada')
                self.assertEqual(schema['statuses']['value'][0], 'success')
        self.assertEqual(len(notif), 3)

    @async_test
    async def test_update_notification(self):
        obj_id = ObjectId()
        slack_notif = SlackNotification(webhook_url='https://bla.nada',
                                        repository_id=obj_id)
        await slack_notif.save()

        self.handler.body = {'repository_id': str(obj_id),
                             'webhook_url': 'https://bla.tudo'}
        await self.handler.update_notification(b'slack-notification')

        notif = await SlackNotification.objects.get(repository_id=obj_id)
        self.assertEqual(notif.webhook_url, 'https://bla.tudo')

    @patch.object(server, 'send_email', AsyncMagicMock(spec=server.send_email))
    @async_test
    async def test_send_email(self):
        recipients = ['a@a.com']
        subject = 'something'
        message = 'not really important'
        self.handler.body = {'recipients': recipients,
                             'subject': subject,
                             'message': message}

        await self.handler.send_email()
        self.assertTrue(server.send_email.called)
