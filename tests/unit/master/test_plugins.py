# -*- coding: utf-8 -*-

# Copyright 2016, 2017 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import MagicMock, patch
from toxicbuild.core.utils import now
from toxicbuild.master.build import BuildSet, Build, Builder, BuildStep
from toxicbuild.master.repository import Repository, RepositoryRevision
from toxicbuild.master.slave import Slave
from toxicbuild.master import plugins, mail
from tests import async_test, AsyncMagicMock


mock_settings = MagicMock()
mock_settings.SMTP_MAIL_FROM = 'tester@somewhere.net'
mock_settings.SMTP_HOST = 'localhost'
mock_settings.SMTP_PORT = 587
mock_settings.SMTP_USERNAME = 'tester'
mock_settings.SMTP_PASSWORD = '123'
mock_settings.SMTP_VALIDATE_CERTS = True
mock_settings.SMTP_STARTTLS = True


class MetaMasterPluginTest(TestCase):

    def setUp(self):

        class TestBasePlugin(plugins.EmbeddedDocument,
                             metaclass=plugins.MetaMasterPlugin):

            name = 'base-plugin'
            type = 'testing'

        self.test_cls = TestBasePlugin

    def test_base_master_plugin(self):
        self.assertEqual(self.test_cls.name, 'base-plugin')


class PrettyFieldTest(TestCase):

    def setUp(self):

        class TestClass(plugins.EmbeddedDocument):

            some_attr = plugins.PrettyStringField(pretty_name='Some Attribute')

        self.test_class = TestClass

    def test_pretty_name(self):
        self.assertEqual(self.test_class.some_attr.pretty_name,
                         'Some Attribute')


class MasterPluginTest(TestCase):

    def setUp(self):

        class TestPlugin(plugins.MasterPlugin):

            name = 'test-plugin'
            type = 'testing'

        self.plugin_class = TestPlugin

    @async_test
    def tearDown(self):
        yield from Repository.drop_collection()

    def test_create_field_dict(self):
        f = plugins.PrettyStringField(pretty_name='bla')
        fdict = plugins.MasterPlugin._create_field_dict(f)
        self.assertEqual(fdict['pretty_name'], 'bla')

    def test_create_field_dict_error(self):
        f = plugins.StringField()
        fdict = plugins.MasterPlugin._create_field_dict(f)
        self.assertEqual(fdict['pretty_name'], '')

    def test_translate_schema(self):
        schema = plugins.MasterPlugin.get_schema()
        translation = plugins.MasterPlugin._translate_schema(schema)
        keys = {'name', 'pretty_name', 'type', 'description', '_cls',
                'uuid'}
        self.assertEqual(set(translation.keys()), keys)

    def test_get_schema(self):
        schema = plugins.MasterPlugin.get_schema()
        self.assertEqual(schema['name'], 'BaseMasterPlugin')

    @async_test
    async def test_to_dict(self):
        await self._create_test_data()
        plugin_dict = self.plugin.to_dict()
        self.assertEqual(plugin_dict['name'], 'test-plugin')

    @async_test
    async def test_run(self):
        await self._create_test_data()
        sender = MagicMock()
        with self.assertRaises(NotImplementedError):
            await self.plugin.run(sender)

    async def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewhere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        await self.repo.save()
        self.plugin = self.plugin_class()
        self.repo.plugins.append(self.plugin)
        self.repo.save()


class NotificationPlugin(TestCase):

    @async_test
    async def tearDown(self):
        await Repository.drop_collection()

    @patch.object(plugins.build_started, 'connect', MagicMock())
    @patch.object(plugins.build_finished, 'connect', MagicMock())
    @async_test
    async def test_run_with_build_started(self):
        await self._create_test_data()
        self.plugin.statuses = ['running']

        await self.plugin.run(sender=MagicMock())
        self.assertTrue(plugins.build_started.connect.called)
        self.assertTrue(plugins.build_finished.connect.called)

    @patch.object(plugins.build_started, 'connect', MagicMock())
    @patch.object(plugins.build_finished, 'connect', MagicMock())
    @async_test
    async def test_run_without_build_started(self):
        await self._create_test_data()
        self.plugin.statuses = ['fail']

        await self.plugin.run(sender=MagicMock())
        self.assertFalse(plugins.build_started.connect.called)
        self.assertTrue(plugins.build_finished.connect.called)

    @patch.object(plugins.build_started, 'disconnect', MagicMock())
    @patch.object(plugins.build_finished, 'disconnect', MagicMock())
    @async_test
    async def test_stop(self):
        await self._create_test_data()
        await self.plugin.stop()
        self.assertTrue(plugins.build_started.disconnect.called)
        self.assertTrue(plugins.build_finished.disconnect.called)

    def test_get_schema_to_serialize(self):
        schema = plugins.NotificationPlugin.get_schema(to_serialize=True)
        expected = {'name': 'statuses', 'type': 'list',
                    'pretty_name': 'Statuses'}
        self.assertEqual(schema['statuses'], expected)
        keys = list(schema.keys())
        self.assertLess(keys.index('branches'), keys.index('statuses'))

    @async_test
    async def test_build_started(self):
        await self._create_test_data()
        self.plugin._check_build = AsyncMagicMock()
        repo, build = MagicMock(), MagicMock()
        self.plugin._build_started(repo, build)
        sig_type = self.plugin._check_build.call_args[0][0]
        self.assertEqual(sig_type, 'started')

    @async_test
    async def test_build_finished(self):
        await self._create_test_data()
        self.plugin._check_build = AsyncMagicMock()
        repo, build = MagicMock(), MagicMock()
        self.plugin._build_finished(repo, build)
        sig_type = self.plugin._check_build.call_args[0][0]
        self.assertEqual(sig_type, 'finished')

    @async_test
    async def test_check_build_started(self):
        await self._create_test_data()
        sig = 'started'
        build = MagicMock()
        buildset = MagicMock()
        buildset.branch = 'master'
        build.get_buildset = AsyncMagicMock(return_value=buildset)
        self.plugin.branches = ['master', 'release']
        self.plugin.sender = self.repo
        self.plugin.send_started_message = AsyncMagicMock()
        self.plugin.send_finished_message = AsyncMagicMock()
        await self.plugin._check_build(sig, self.repo, build)
        self.assertTrue(self.plugin.send_started_message.called)

    @async_test
    async def test_check_build_finished(self):
        await self._create_test_data()
        sig = 'finished'
        build = MagicMock()
        buildset = MagicMock()
        buildset.branch = 'master'
        build.get_buildset = AsyncMagicMock(return_value=buildset)
        self.plugin.branches = ['master', 'release']
        self.plugin.sender = self.repo
        self.plugin.send_started_message = AsyncMagicMock()
        self.plugin.send_finished_message = AsyncMagicMock()
        await self.plugin._check_build(sig, self.repo, build)
        self.assertTrue(self.plugin.send_finished_message.called)

    @async_test
    async def test_check_build_finished_wrong_branch(self):
        await self._create_test_data()
        sig = 'finished'
        build = MagicMock()
        buildset = MagicMock()
        buildset.branch = 'feature-1'
        build.get_buildset = AsyncMagicMock(return_value=buildset)
        self.plugin.branches = ['master', 'release']
        self.plugin.sender = self.repo
        self.plugin.send_started_message = AsyncMagicMock()
        self.plugin.send_finished_message = AsyncMagicMock()
        await self.plugin._check_build(sig, self.repo, build)
        self.assertFalse(self.plugin.send_finished_message.called)

    @async_test
    async def test_check_build_finished_wrong_repo(self):
        await self._create_test_data()
        sig = 'finished'
        build = MagicMock()
        buildset = MagicMock()
        buildset.branch = 'master'
        build.get_buildset = AsyncMagicMock(return_value=buildset)
        self.plugin.branches = ['master', 'release']
        self.plugin.sender = MagicMock()
        self.plugin.send_started_message = AsyncMagicMock()
        self.plugin.send_finished_message = AsyncMagicMock()
        await self.plugin._check_build(sig, self.repo, build)
        self.assertFalse(self.plugin.send_finished_message.called)

    @async_test
    async def test_send_started_message(self):
        repo, build = MagicMock(), MagicMock()
        p = plugins.NotificationPlugin()
        with self.assertRaises(NotImplementedError):
            await p.send_started_message(repo, build)

    @async_test
    async def test_send_finished_message(self):
        repo, build = MagicMock(), MagicMock()
        p = plugins.NotificationPlugin()
        with self.assertRaises(NotImplementedError):
            await p.send_finished_message(repo, build)

    async def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        await self.repo.save()
        self.plugin = plugins.NotificationPlugin(branches=['master'],
                                                 statuses=['fail', 'success'])
        self.repo.plugins.append(self.plugin)
        self.repo.save()


class SlackPluginTest(TestCase):

    @async_test
    async def tearDown(self):
        await Repository.drop_collection()

    @patch.object(plugins.requests, 'post', MagicMock())
    @async_test
    async def test_send_message(self):
        await self._create_test_data()
        post = MagicMock()
        plugins.requests.post = asyncio.coroutine(
            lambda *a, **kw: post(*a, **kw))
        msg = {'text': 'something happend'}
        await self.plugin._send_message(msg)
        called = post.call_args
        self.assertEqual(called[0][0], self.plugin.webhook_url)
        self.assertEqual(called[1]['data'], plugins.json.dumps(msg))
        self.assertEqual(called[1]['headers'],
                         {'Content-Type': 'application/json'})

    @async_test
    async def test_send_started_message(self):
        await self._create_test_data()
        self.plugin._send_message = MagicMock(spec=self.plugin._send_message)
        build = MagicMock()
        build.started = now()
        dt = plugins.datetime2string(build.started)
        txt = '[my-test-repo] Build *started* at *{}*'.format(dt)
        expected = {'text': txt, 'username': 'ToxicBuild',
                    'channel': self.plugin.channel_name}
        await self.plugin.send_started_message(self.repo, build)
        called = self.plugin._send_message.call_args[0][0]
        self.assertEqual(called, expected, called)

    @async_test
    async def test_send_finished_message(self):
        await self._create_test_data()
        send_msg = MagicMock(spec=self.plugin._send_message)
        self.plugin._send_message = asyncio.coroutine(
            lambda *a, **kw: send_msg(*a, **kw))
        build = MagicMock()
        build.finished = now()
        build.status = 'success'
        dt = plugins.datetime2string(build.finished)
        txt = '[my-test-repo] Build *finished* at *{}* with status *{}*'
        txt = txt.format(dt, build.status)
        expected = {'text': txt, 'username': 'ToxicBuild',
                    'channel': self.plugin.channel_name}

        await self.plugin.send_finished_message(self.repo, build)
        called = send_msg.call_args[0][0]
        self.assertEqual(called, expected, called)

    @async_test
    async def test_send_finished_message_with_bad_status(self):
        await self._create_test_data()
        self.plugin._send_message = MagicMock(spec=self.plugin._send_message)
        build = MagicMock()
        build.finished = now()
        build.status = 'warning'
        await self.plugin.send_finished_message(self.repo, build)
        self.assertFalse(self.plugin._send_message.called)

    async def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        await self.repo.save()
        url = 'https://some-slack-url.bla/xxxx/yyyy'
        self.plugin = plugins.SlackPlugin(branches=['master'],
                                          webhook_url=url,
                                          statuses=['fail', 'success'])
        self.repo.plugins.append(self.plugin)
        self.repo.save()


class EmailPluginTest(TestCase):

    @async_test
    async def tearDown(self):
        await Repository.drop_collection()

    @patch.object(mail, 'settings', mock_settings)
    @patch.object(plugins.MailSender, 'connect', AsyncMagicMock())
    @patch.object(plugins.MailSender, 'disconnect', AsyncMagicMock())
    @patch.object(plugins.MailSender, 'send', AsyncMagicMock())
    @async_test
    async def test_send_started_message(self):
        await self._create_test_data()
        build = MagicMock()
        build.started = now()
        build.get_buildset = AsyncMagicMock()
        build.get_buildset.return_value.commit = '0980s9fas9f'
        build.get_buildset.return_value.title = 'some cool stuff'
        repo = MagicMock()
        repo.name = 'My Project'
        await self.plugin.send_started_message(repo, build)
        self.assertTrue(plugins.MailSender.send.called)

    @patch.object(mail, 'settings', mock_settings)
    @patch.object(plugins.MailSender, 'connect', AsyncMagicMock())
    @patch.object(plugins.MailSender, 'disconnect', AsyncMagicMock())
    @patch.object(plugins.MailSender, 'send', AsyncMagicMock())
    @async_test
    async def test_send_finished_message(self):
        await self._create_test_data()
        build = MagicMock()
        build.finished = now()
        build.get_buildset = AsyncMagicMock()
        build.get_buildset.return_value.title = 'commit title'
        build.get_buildset.return_value.commit = 'asdfçlj'
        build.buildset.commit = '0980s9fas9f'
        build.buildset.title = 'some cool stuff in this commit'
        repo = MagicMock()
        repo.name = 'My Project'
        await self.plugin.send_finished_message(repo, build)
        self.assertTrue(plugins.MailSender.send.called)

    async def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        await self.repo.save()
        self.plugin = plugins.EmailPlugin(branches=['master'],
                                          statuses=['fail', 'success'],
                                          recipients=['me@me.com'])
        self.repo.plugins.append(self.plugin)
        self.repo.save()


class CustomWebhookPluginTest(TestCase):

    @async_test
    async def tearDown(self):
        await Repository.drop_collection()
        await Slave.drop_collection()
        await BuildSet.drop_collection()
        await Builder.drop_collection()

    @patch.object(plugins.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_send_message(self):
        await self._create_test_data()
        await self.plugin._send_message(self.repo, self.buildset.builds[0])
        called_url = plugins.requests.post.call_args[0][0]
        self.assertEqual(called_url, self.plugin.webhook_url)

    @patch.object(plugins.CustomWebhookPlugin, '_send_message',
                  AsyncMagicMock())
    @async_test
    async def test_send_started_message(self):
        await self._create_test_data()
        await self.plugin.send_started_message(
            self.repo, self.buildset.builds[0])
        self.assertTrue(self.plugin._send_message.called)

    @patch.object(plugins.CustomWebhookPlugin, '_send_message',
                  AsyncMagicMock())
    @async_test
    async def test_send_finished_message(self):
        await self._create_test_data()
        await self.plugin.send_finished_message(
            self.repo, self.buildset.builds[0])
        self.assertTrue(self.plugin._send_message.called)

    async def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        await self.repo.save()
        self.plugin = plugins.CustomWebhookPlugin(
            branches=['master'], statuses=['fail', 'success'],
            webhook_url='http://something.com/bla')
        self.repo.plugins.append(self.plugin)
        self.repo.save()

        self.slave = Slave(name='sla', host='localhost', port=1234,
                           token='123')
        await self.slave.save()
        self.builder = Builder(repository=self.repo, name='builder-bla')
        await self.builder.save()
        b = Build(branch='master', builder=self.builder,
                  repository=self.repo, slave=self.slave,
                  named_tree='v0.1')
        s = BuildStep(name='some step', output='some output',
                      command='some command')
        b.steps.append(s)
        self.rev = RepositoryRevision(commit='saçfijf',
                                      commit_date=now(),
                                      repository=self.repo,
                                      branch='master',
                                      author='tião',
                                      title='blabla')
        await self.rev.save()

        self.buildset = await BuildSet.create(repository=self.repo,
                                              revision=self.rev)
        self.buildset.builds.append(b)
        await self.buildset.save()
