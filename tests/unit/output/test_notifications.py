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

from bson.objectid import ObjectId
from unittest import TestCase
from unittest.mock import patch, MagicMock
from toxicbuild.integrations import github, gitlab
from toxicbuild.core.utils import (datetime2string, now, localtime2utc)
from toxicbuild.master.users import User
from toxicbuild.output import notifications
from tests import async_test, AsyncMagicMock


class MetaNotificationTest(TestCase):

    def setUp(self):

        class TestBasePlugin(notifications.Document,
                             metaclass=notifications.MetaNotification):

            name = 'test-notification'

        self.test_cls = TestBasePlugin

    def test_base_master_plugin(self):
        self.assertEqual(self.test_cls.name, 'test-notification')


class NotificationTest(TestCase):

    @async_test
    async def setUp(self):

        class TestNotification(notifications.Notification):

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
        await notifications.Notification.drop_collection()

    def test_create_field_dict(self):
        f = notifications.PrettyStringField(pretty_name='bla')
        fdict = notifications.Notification._create_field_dict(f)
        self.assertEqual(fdict['pretty_name'], 'bla')

    def test_create_field_dict_error(self):
        f = notifications.StringField()
        fdict = notifications.Notification._create_field_dict(f)
        self.assertEqual(fdict['pretty_name'], '')

    def test_get_schema(self):
        schema = notifications.Notification.get_schema()
        self.assertEqual(schema['name'], 'BaseNotification')

    def test_translate_schema(self):
        translation = notifications.Notification.get_schema(to_serialize=True)
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

        self.notification.send_started_message = AsyncMagicMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMagicMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertFalse(self.notification.send_started_message.called)
        self.assertFalse(self.notification.send_finished_message.called)

    @async_test
    async def test_run_bad_branch(self):
        self.notification.branches = ['release']
        buildset_info = {'status': 'fail', 'branch': 'master',
                         'repository': {'id': 'some-id'}}

        self.notification.send_started_message = AsyncMagicMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMagicMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertFalse(self.notification.send_started_message.called)
        self.assertFalse(self.notification.send_finished_message.called)

    @async_test
    async def test_run_send_started_message(self):
        self.notification.statuses = []
        buildset_info = {'status': 'running', 'branch': 'master',
                         'repository': {'id': 'some-id'}}

        self.notification.send_started_message = AsyncMagicMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMagicMock(
            spec=self.notification.send_finished_message)

        await self.notification.run(buildset_info)

        self.assertTrue(self.notification.send_started_message.called)
        self.assertFalse(self.notification.send_finished_message.called)

    @async_test
    async def test_run_send_finished_message(self):
        self.notification.statuses = []
        buildset_info = {'status': 'success', 'branch': 'master',
                         'repository': {'id': 'some-id'}}
        sender = AsyncMagicMock()
        sender.id = 'some-id'

        self.notification.send_started_message = AsyncMagicMock(
            spec=self.notification.send_started_message)
        self.notification.send_finished_message = AsyncMagicMock(
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

        class MyNotification(notifications.Notification):

            name = 'my-notification'
            events = ['bla', 'ble']
            no_list = True

        obj_id = ObjectId()
        notif = MyNotification(repository_id=obj_id)
        await notif.save()

        qs = notifications.Notification.get_repo_notifications(obj_id, 'bla')
        count = await qs.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_get_repo_notifications_no_event(self):
        class MyNotification(notifications.Notification):

            name = 'my-notification'
            events = []
            no_list = True

        notif = MyNotification(repository_id=self.obj_id)
        await notif.save()

        qs = notifications.Notification.get_repo_notifications(self.obj_id)

        f = await qs.first()
        count = await qs.count()
        self.assertEqual(count, 1)
        self.assertEqual('my-notification', f.name)


class SlackNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        obj_id = ObjectId()
        sender = {'id': 'some-id',
                  'name': 'some-name'}

        self.notification = notifications.SlackNotification(
            repository_id=obj_id, branches=['master', 'other'],
            statuses=['success', 'fail'], webhook_url='https://someurl.nada')
        self.notification.sender = sender
        await self.notification.save()

    @async_test
    async def tearDown(self):
        await notifications.Notification.drop_collection()

    @patch.object(notifications.requests, 'post', AsyncMagicMock(
        spec=notifications.requests.post, return_value=MagicMock()))
    @async_test
    async def test_send_message(self):
        message = {'some': 'thing'}
        await self.notification._send_message(message)
        self.assertTrue(notifications.requests.post.called)

    @async_test
    async def test_send_started_message(self):

        buildset_info = {'started': '01/01/1970 00:00:00'}
        self.notification._send_message = AsyncMagicMock(
            self.notification._send_message)
        await self.notification.send_started_message(buildset_info)
        self.assertTrue(self.notification._send_message.called)

    @async_test
    async def test_send_finished_message(self):
        buildset_info = {'finished': '01/01/1970 00:00:00',
                         'status': 'success'}
        self.notification._send_message = AsyncMagicMock(
            self.notification._send_message)
        await self.notification.send_finished_message(buildset_info)
        self.assertTrue(self.notification._send_message.called)


class EmailNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        obj_id = ObjectId()
        self.notification = notifications.EmailNotification(
            repository_id=obj_id,
            recipients=['a@a.com'])
        self.notification.sender = {'id': 'some-id', 'name': 'some-name'}
        await self.notification.save()

    @patch.object(notifications.MailSender, 'send', AsyncMagicMock(
        spec=notifications.MailSender.send))
    @patch.object(notifications.MailSender, 'connect', AsyncMagicMock(
        spec=notifications.MailSender.connect))
    @patch.object(notifications.MailSender, 'disconnect', AsyncMagicMock(
        spec=notifications.MailSender.disconnect))
    @patch.object(notifications, 'settings', MagicMock())
    @async_test
    async def test_send_started_message(self):
        buildset_info = {'started': 'here is a datetime string',
                         'commit': '123adf', 'title': 'Some change'}
        await self.notification.send_started_message(buildset_info)
        self.assertTrue(notifications.MailSender.send.called)

    @patch.object(notifications.MailSender, 'send', AsyncMagicMock(
        spec=notifications.MailSender.send))
    @patch.object(notifications.MailSender, 'connect', AsyncMagicMock(
        spec=notifications.MailSender.connect))
    @patch.object(notifications.MailSender, 'disconnect', AsyncMagicMock(
        spec=notifications.MailSender.disconnect))
    @patch.object(notifications, 'settings', MagicMock())
    @async_test
    async def test_send_finished_message(self):
        buildset_info = {'finished': 'here is a datetime string',
                         'commit': '123adf', 'title': 'Some change',
                         'status': 'fail', 'total_time': '0:03:01'}
        await self.notification.send_finished_message(buildset_info)
        self.assertTrue(notifications.MailSender.send.called)


class CustomWebhookNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        obj_id = ObjectId()
        self.notification = notifications.CustomWebhookNotification(
            webhook_url='https://somwhere.nada',
            repository_id=obj_id)
        await self.notification.save()

    @patch.object(notifications.requests, 'post', AsyncMagicMock(
        spec=notifications.requests.post, return_value=MagicMock()))
    @async_test
    async def test_send_message(self):
        buildset_info = {'repository': {'id': 'some-id', 'name': 'some-name'}}
        await self.notification._send_message(buildset_info)
        self.assertTrue(notifications.requests.post)

    @async_test
    async def test_send_started_message(self):
        self.notification._send_message = AsyncMagicMock(
            spec=self.notification._send_message)
        await self.notification.send_started_message({})
        self.assertTrue(self.notification._send_message.called)

    @async_test
    async def test_send_finished_message(self):
        self.notification._send_message = AsyncMagicMock(
            spec=self.notification._send_message)
        await self.notification.send_finished_message({})
        self.assertTrue(self.notification._send_message.called)


class GithubCheckRunNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = User(email='a@a.com')
        await self.user.save()
        self.installation = github.GithubInstallation(
            github_id=1234, user=self.user)
        await self.installation.save()

        await self.installation.save()
        self.check_run = notifications.GithubCheckRunNotification(
            installation=self.installation)

    @async_test
    async def tearDown(self):
        await User.drop_collection()
        await github.GithubInstallation.drop_collection()

    @async_test
    async def test_run(self):
        info = {'status': 'fail', 'id': 'some-id',
                'repository': {'id': 'some-repo-id'}}
        self.check_run._send_message = AsyncMagicMock(
            spec=self.check_run._send_message)

        await self.check_run.run(info)
        self.assertTrue(self.check_run._send_message.called)

    def test_get_payload(self):
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'started': None}
        run_status = 'pending'
        conclusion = None
        expected = {'name': self.check_run.run_name,
                    'head_branch': 'master',
                    'head_sha': '123adf',
                    'status': run_status}
        payload = self.check_run._get_payload(buildset_info, run_status,
                                              conclusion)
        self.assertEqual(payload, expected)

    def test_get_payload_completed(self):
        started = localtime2utc(now())
        finished = localtime2utc(now())
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'started': datetime2string(started),
                         'finished': datetime2string(finished)}

        run_status = 'completed'
        started_at = datetime2string(
            started,
            dtformat="%Y-%m-%dT%H:%M:%S%z").replace('+0000', 'Z')
        completed_at = datetime2string(
            finished,
            dtformat="%Y-%m-%dT%H:%M:%S%z").replace('+0000', 'Z')
        conclusion = None
        expected = {'name': self.check_run.run_name,
                    'head_branch': 'master',
                    'head_sha': '123adf',
                    'started_at': started_at,
                    'status': run_status,
                    'completed_at': completed_at,
                    'conclusion': conclusion}

        payload = self.check_run._get_payload(buildset_info, run_status,
                                              conclusion)
        self.assertEqual(payload, expected)

    @patch.object(github.requests, 'post', AsyncMagicMock(
        spec=github.requests.post))
    @patch.object(github.GithubInstallation, 'get_header', AsyncMagicMock(
        spec=github.GithubInstallation.get_header))
    @async_test
    async def test_send_message(self):
        self.check_run.sender = {'id': 'some-id',
                                 'full_name': 'bla/ble',
                                 'external_full_name': 'ble/ble'}
        started = localtime2utc(now())
        finished = localtime2utc(now())
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'started': datetime2string(started),
                         'finished': datetime2string(finished),
                         'id': 'some-id'}

        run_status = 'completed'
        conclusion = None
        ret = MagicMock()
        ret.text = ''
        ret.status = 201
        github.requests.post.return_value = ret

        await self.check_run._send_message(buildset_info, run_status,
                                           conclusion)
        self.assertTrue(github.requests.post.called)


class GitlabCommitStatusNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = User(email='a@a.com')
        await self.user.save()
        self.installation = gitlab.GitLabInstallation(
            gitlab_user_id=1234, user=self.user)
        await self.installation.save()

        await self.installation.save()
        self.notif = notifications.GitlabCommitStatusNotification(
            installation=self.installation)

    @async_test
    async def tearDown(self):
        await User.drop_collection()
        await gitlab.GitLabInstallation.drop_collection()

    @async_test
    async def test_run(self):
        info = {'status': 'fail', 'id': 'some-id',
                'repository': {'id': 'some-repo-id'}}
        self.notif._send_message = AsyncMagicMock(
            spec=self.notif._send_message)

        await self.notif.run(info)
        self.assertTrue(self.notif._send_message.called)

    @patch.object(gitlab.requests, 'post', AsyncMagicMock(
        spec=gitlab.requests.post))
    @patch.object(gitlab.GitLabInstallation, 'get_header', AsyncMagicMock(
        spec=gitlab.GitLabInstallation.get_header))
    @async_test
    async def test_send_message(self):
        self.notif.sender = {'id': 'some-id',
                             'full_name': 'bla/ble',
                             'external_full_name': 'ble/ble'}
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'status': 'exception',
                         'id': 'some-id'}

        ret = MagicMock()
        ret.text = ''
        ret.status = 201
        github.requests.post.return_value = ret

        await self.notif._send_message(buildset_info)
        self.assertTrue(gitlab.requests.post.called)
