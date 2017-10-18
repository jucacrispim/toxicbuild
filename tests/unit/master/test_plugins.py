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
from toxicbuild.master import Repository
from toxicbuild.master import plugins
from tests import async_test


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
        self.assertTrue(translation['branches'], 'list')

    def test_get_schema(self):
        schema = plugins.MasterPlugin.get_schema()
        self.assertEqual(schema['name'], 'BaseMasterPlugin')

    def test_get_schema_to_serialize(self):
        schema = plugins.MasterPlugin.get_schema(to_serialize=True)
        expected = {'name': 'statuses', 'type': 'list',
                    'pretty_name': 'Statuses'}
        self.assertEqual(schema['statuses'], expected)
        keys = list(schema.keys())
        self.assertLess(keys.index('branches'), keys.index('statuses'))

    @async_test
    def test_to_dict(self):
        yield from self._create_test_data()
        plugin_dict = self.plugin.to_dict()
        self.assertEqual(plugin_dict['name'], 'test-plugin')

    @async_test
    def test_run(self):
        yield from self._create_test_data()
        with self.assertRaises(NotImplementedError):
            yield from self.plugin.run()

    @asyncio.coroutine
    def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewhere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        yield from self.repo.save()
        self.plugin = self.plugin_class(branches=['master'])
        self.repo.plugins.append(self.plugin)
        self.repo.save()


class SlackPluginTest(TestCase):

    @async_test
    def tearDown(self):
        yield from Repository.drop_collection()

    @patch.object(plugins.build_started, 'connect', MagicMock())
    @patch.object(plugins.build_finished, 'connect', MagicMock())
    @async_test
    def test_run_with_build_started(self):
        yield from self._create_test_data()
        self.plugin.statuses = ['running']

        yield from self.plugin.run()
        self.assertTrue(plugins.build_started.connect.called)
        self.assertTrue(plugins.build_finished.connect.called)

    @patch.object(plugins.build_started, 'connect', MagicMock())
    @patch.object(plugins.build_finished, 'connect', MagicMock())
    @async_test
    def test_run_without_build_started(self):
        yield from self._create_test_data()
        self.plugin.statuses = ['fail']

        yield from self.plugin.run()
        self.assertFalse(plugins.build_started.connect.called)
        self.assertTrue(plugins.build_finished.connect.called)

    @patch.object(plugins.build_started, 'disconnect', MagicMock())
    @patch.object(plugins.build_finished, 'disconnect', MagicMock())
    @async_test
    def test_stop(self):
        yield from self._create_test_data()
        yield from self.plugin.stop()
        self.assertTrue(plugins.build_started.disconnect.called)
        self.assertTrue(plugins.build_finished.disconnect.called)

    @patch.object(plugins.requests, 'post', MagicMock())
    @async_test
    def test_send_msg(self):
        yield from self._create_test_data()
        msg = {'text': 'something happend'}
        yield from self.plugin._send_msg(msg)
        called = plugins.requests.post.call_args
        self.assertEqual(called[0][0], self.plugin.webhook_url)
        self.assertEqual(called[1]['data'], msg)
        self.assertEqual(called[1]['headers'],
                         {'content-type': 'application/json'})

    @async_test
    def test_send_started_msg(self):
        yield from self._create_test_data()
        self.plugin._send_msg = MagicMock(spec=self.plugin._send_msg)
        build = MagicMock()
        build.started = now()
        dt = plugins.datetime2string(build.started)
        txt = '[my-test-repo] Build *started* at *{}*'.format(dt)
        expected = {'text': txt}
        yield from self.plugin.send_started_msg(self.repo, build)
        called = self.plugin._send_msg.call_args[0][0]
        self.assertEqual(called, expected, called)

    @async_test
    def test_send_finished_msg(self):
        yield from self._create_test_data()
        self.plugin._send_msg = MagicMock(spec=self.plugin._send_msg)
        build = MagicMock()
        build.finished = now()
        build.status = 'success'
        dt = plugins.datetime2string(build.finished)
        txt = '[my-test-repo] Build *finished* at *{}*'.format(dt)
        expected = {'text': txt}
        yield from self.plugin.send_finished_msg(self.repo, build)
        called = self.plugin._send_msg.call_args[0][0]
        self.assertEqual(called, expected, called)

    @async_test
    def test_send_finished_msg_with_bad_status(self):
        yield from self._create_test_data()
        self.plugin._send_msg = MagicMock(spec=self.plugin._send_msg)
        build = MagicMock()
        build.finished = now()
        build.status = 'warning'
        yield from self.plugin.send_finished_msg(self.repo, build)
        self.assertFalse(self.plugin._send_msg.called)

    @asyncio.coroutine
    def _create_test_data(self):
        self.repo = Repository(name='my-test-repo',
                               url='git@somewere.com/bla.git',
                               update_seconds=300,
                               vcs_type='git')
        yield from self.repo.save()
        url = 'https://some-slack-url.bla/xxxx/yyyy'
        self.plugin = plugins.SlackPlugin(branches=['master'],
                                          webhook_url=url,
                                          statuses=['fail', 'success'])
        self.repo.plugins.append(self.plugin)
        self.repo.save()
