# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import MagicMock, Mock, patch
from toxicbuild.slave import plugins, build
from tests import async_test


class MyPlugin(plugins.Plugin):
    name = 'my-plugin'


class PluginTest(TestCase):

    def setUp(self):
        self.plugin = MyPlugin()

    def test_get(self):

        plugin = plugins.Plugin.get('my-plugin')
        self.assertEqual(plugin, type(self.plugin))

    def test_get_without_a_plugin(self):
        with self.assertRaises(plugins.PluginNotFound):
            plugins.Plugin.get('i-dont-exist')

    def test_get_steps_before(self):
        self.assertEqual([], self.plugin.get_steps_before())

    def test_get_steps_after(self):
        self.assertEqual([], self.plugin.get_steps_after())

    def test_get_env_vars(self):
        self.assertEqual({}, self.plugin.get_env_vars())


class PythonCreateVenvStepTest(TestCase):

    def setUp(self):
        super().setUp()

        self.step = plugins.PythonCreateVenvStep(venv_dir='bla/venv',
                                                 pyversion='python3.4')

    @patch.object(plugins.os.path, 'exists', Mock())
    @async_test
    def test_execute_with_existing_venv(self):
        step_info = yield from self.step.execute('some/dir')
        self.assertIn('venv exists', step_info['output'])
        self.assertEqual(plugins.os.path.exists.call_args[0][0],
                         'some/dir/bla/venv/bin/python')

    @patch.object(build, 'exec_cmd', MagicMock())
    @async_test
    def test_execute_with_new_venv(self):
        execute_mock = Mock(spec=plugins.BuildStep.execute)
        build.exec_cmd = asyncio.coroutine(
            lambda *a, **kw: execute_mock(*a, **kw))

        yield from self.step.execute('.')
        self.assertTrue(execute_mock.called)


class PythonVenvPluginTest(TestCase):

    def setUp(self):
        self.plugin = plugins.PythonVenvPlugin(pyversion='/usr/bin/python3.4')

    def test_name(self):
        self.assertEqual(self.plugin.name, 'python-venv')

    def test_get_steps_before(self):
        expected = [
            plugins.BuildStep(
                'create venv',
                'virtualenv venv-usrbinpython3.4 -p /usr/bin/python3.4'),
            plugins.BuildStep('install dependencies using pip',
                              'pip install -r requirements.txt')
        ]

        steps_before = self.plugin.get_steps_before()

        self.assertEqual(expected, steps_before)

    def test_get_steps_after_without_remove(self):
        expected = []
        steps_after = self.plugin.get_steps_after()

        self.assertEqual(expected, steps_after)

    def test_get_steps_after_removing(self):
        expected = [plugins.BuildStep(
            'remove venv', 'rm -rf venv-usrbinpython3.4')]
        self.plugin.remove_env = True
        steps_after = self.plugin.get_steps_after()

        self.assertEqual(expected, steps_after)

    def test_get_env_vars(self):
        expected = {'PATH': 'venv-usrbinpython3.4/bin:PATH'}
        env_vars = self.plugin.get_env_vars()

        self.assertEqual(expected, env_vars)


class AptitudeInstallPluginTest(TestCase):

    def setUp(self):
        packages = ['libawesome', 'libawesome-dev']
        self.plugin = plugins.AptitudeInstallPlugin(packages=packages)

    def test_name(self):
        self.assertEqual(self.plugin.name, 'aptitude-install')

    def test_get_steps_before(self):
        expected = [
            plugins.BuildStep(
                'Installing packages with aptitude',
                'sudo aptitude install -y libawesome libawesome-dev'),
        ]

        steps_before = self.plugin.get_steps_before()

        self.assertEqual(expected, steps_before)
