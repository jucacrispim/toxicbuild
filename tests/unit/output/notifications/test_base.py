# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from unittest import TestCase
from unittest.mock import AsyncMock

from bson.objectid import ObjectId

from toxicbuild.output.notifications import base

from tests import async_test


class MetaNotificationTest(TestCase):

    def setUp(self):

        class TestBasePlugin(base.Document,
                             metaclass=base.MetaNotification):

            name = 'test-notification'

        self.test_cls = TestBasePlugin

    def test_base_master_plugin(self):
        self.assertEqual(self.test_cls.name, 'test-notification')


class NotificationTest(TestCase):

    @async_test
    async def setUp(self):

        class TestNotification(base.Notification):

            name = 'test-notification'
            no_list = True

        self.notification_class = TestNotification
        self.obj_id = ObjectId()
        self.notification = self.notification_class(
            repository_id=self.obj_id, branches=['master', 'other'],
            statuses=['success', 'fail'])
        await self.notification.save()

    @async_test
    async def tearDown(self):
        await base.Notification.drop_collection()

    def test_create_field_dict(self):
        f = base.PrettyStringField(pretty_name='bla')
        fdict = base.Notification._create_field_dict(f)
        self.assertEqual(fdict['pretty_name'], 'bla')

    def test_create_field_dict_error(self):
        f = base.StringField()
        fdict = base.Notification._create_field_dict(f)
        self.assertEqual(fdict['pretty_name'], '')

    def test_get_schema(self):
        schema = base.Notification.get_schema()
        self.assertEqual(schema['name'], 'BaseNotification')

    def test_translate_schema(self):
        translation = base.Notification.get_schema(to_serialize=True)
        keys = {'name', 'pretty_name', 'description', '_cls',
                'branches', 'statuses', 'repository_id'}
        self.assertEqual(set(translation.keys()), keys)

    @async_test
    async def test_to_dict(self):
        plugin_dict = self.notification.to_dict()
        self.assertEqual(plugin_dict['name'], 'test-notification')

    @async_test
    async def test_run_bad_status(self):
        self.notification.statuses = ['success']
        buildset_info = {'status': 'fail', 'branch': 'master',
                         'repository': {'id': 'some-id'}}

        self.notification.send_started_message = AsyncMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertFalse(self.notification.send_started_message.called)
        self.assertFalse(self.notification.send_finished_message.called)

    @async_test
    async def test_run_bad_branch(self):
        self.notification.branches = ['release']
        buildset_info = {'status': 'fail', 'branch': 'master',
                         'repository': {'id': 'some-id'}}

        self.notification.send_started_message = AsyncMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertFalse(self.notification.send_started_message.called)
        self.assertFalse(self.notification.send_finished_message.called)

    @async_test
    async def test_run_send_started_message(self):
        self.notification.statuses = []
        buildset_info = {'status': 'running', 'branch': 'master',
                         'repository': {'id': 'some-id'}}

        self.notification.send_started_message = AsyncMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertTrue(self.notification.send_started_message.called)
        self.assertFalse(self.notification.send_finished_message.called)

    @async_test
    async def test_run_send_finished_message(self):
        self.notification.statuses = []
        buildset_info = {'status': 'success', 'branch': 'master',
                         'repository': {'id': 'some-id'}}
        sender = AsyncMock()
        sender.id = 'some-id'

        self.notification.send_started_message = AsyncMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertFalse(self.notification.send_started_message.called)
        self.assertTrue(self.notification.send_finished_message.called)

    @async_test
    async def test_send_started_message(self):
        with self.assertRaises(NotImplementedError):
            await self.notification.send_started_message({})

    @async_test
    async def test_send_finished_message(self):
        with self.assertRaises(NotImplementedError):
            await self.notification.send_finished_message({})

    @async_test
    async def test_get_repo_notifications_with_event(self):

        class MyNotification(base.Notification):

            name = 'my-notification'
            events = ['bla', 'ble']
            no_list = True

        obj_id = ObjectId()
        notif = MyNotification(repository_id=obj_id)
        await notif.save()

        qs = base.Notification.get_repo_notifications(obj_id, 'bla')
        count = await qs.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_get_repo_notifications_no_event(self):
        class MyNotification(base.Notification):

            name = 'my-notification'
            events = []
            no_list = True

        notif = MyNotification(repository_id=self.obj_id)
        await notif.save()

        qs = base.Notification.get_repo_notifications(self.obj_id)

        f = await qs.first()
        count = await qs.count()
        self.assertEqual(count, 1)
        self.assertEqual('my-notification', f.name)
