# -*- coding: utf-8 -*-

# Copyright 2015-2016, 2018 Juca Crispim <juca@poraodojuca.net>

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
from tests import async_test, AsyncMagicMock


class MyPlugin(plugins.SlavePlugin):
    name = 'my-plugin'


class PluginTest(TestCase):

    def setUp(self):
        self.plugin = MyPlugin()

    def test_get_steps_before(self):
        self.assertEqual([], self.plugin.get_steps_before())

    def test_get_steps_after(self):
        self.assertEqual([], self.plugin.get_steps_after())

    def test_get_env_vars(self):
        self.assertEqual({}, self.plugin.get_env_vars())

    def test_data_dir_without_settings(self):
        expected = '.././my-plugin'
        self.assertEqual(expected, self.plugin.data_dir)

    @patch.object(plugins, 'settings', Mock())
    def test_data_dir_with_settings(self):
        plugins.settings.PLUGINS_DATA_DIR = '/some/dir/'
        expected = '/some/dir/my-plugin'
        self.assertEqual(expected, self.plugin.data_dir)

    @patch.object(plugins.os.path, 'exists', Mock(return_value=True))
    @patch.object(plugins, 'run_in_thread', AsyncMagicMock())
    @async_test
    async def test_create_data_dir_already_exists(self):
        await self.plugin.create_data_dir()
        self.assertFalse(plugins.run_in_thread.called)

    @patch.object(plugins.os.path, 'exists', Mock(return_value=False))
    @patch.object(plugins, 'run_in_thread', AsyncMagicMock())
    @async_test
    async def test_create_data_dir(self):
        await self.plugin.create_data_dir()
        expected = ((plugins.os.makedirs, self.plugin.data_dir), {})
        called = plugins.run_in_thread.call_args
        self.assertEqual(expected, called)


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
        cmd = 'virtualenv .././python-venv/venv-usrbinpython3.4'
        cmd += ' -p /usr/bin/python3.4'
        expected = [
            plugins.BuildStep('create venv', cmd),
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
            'remove venv', 'rm -rf .././python-venv/venv-usrbinpython3.4')]
        self.plugin.remove_env = True
        steps_after = self.plugin.get_steps_after()

        self.assertEqual(expected, steps_after)

    def test_get_env_vars(self):
        expected = {'PATH': '.././python-venv/venv-usrbinpython3.4/bin:PATH'}
        env_vars = self.plugin.get_env_vars()

        self.assertEqual(expected, env_vars)


class AptInstallPluginTest(TestCase):

    def setUp(self):
        packages = ['libawesome', 'libawesome-dev']
        self.plugin = plugins.AptInstallPlugin(packages=packages)

    def test_name(self):
        self.assertEqual(self.plugin.name, 'apt-install')

    def test_env_vars(self):
        self.assertEqual(self.plugin.get_env_vars()['DEBIAN_FRONTEND'],
                         'noninteractive')

    def test_get_steps_before(self):
        expected = [
            plugins.AptUpdateStep(),
            plugins.AptInstallStep(self.plugin.packages)
        ]

        steps_before = self.plugin.get_steps_before()

        self.assertEqual(expected, steps_before)
        self.assertTrue(expected[0].command.startswith('sudo'))


class AptInstallStepTest(TestCase):

    def setUp(self):
        self.step = plugins.AptInstallStep(['somepkg', 'otherpkg'])

    @patch.object(plugins, 'exec_cmd', AsyncMagicMock(return_value='2'))
    @async_test
    async def test_is_everything_installed(self):
        expected = 'sudo dpkg -l | egrep \'somepkg|otherpkg\' | wc -l'
        await self.step._is_everything_installed()
        called = plugins.exec_cmd.call_args[0][0]
        self.assertEqual(called, expected)

    @patch.object(plugins.BuildStep, 'execute', AsyncMagicMock())
    @async_test
    async def test_execute_everything_installed(self):
        self.step._is_everything_installed = AsyncMagicMock(return_value=True)
        await self.step.execute('.')
        self.assertEqual(self.step.command,
                         'sudo dpkg-reconfigure somepkg otherpkg')

    @patch.object(plugins.BuildStep, 'execute', AsyncMagicMock())
    @async_test
    async def test_execute(self):
        self.step._is_everything_installed = AsyncMagicMock(return_value=False)
        await self.step.execute('.')
        self.assertEqual(self.step.command, self.step.install_cmd)
