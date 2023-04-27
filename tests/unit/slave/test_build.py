# -*- coding: utf-8 -*-

# Copyright 2015-2019, 2023 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
import os
from unittest import mock, TestCase
from unittest.mock import AsyncMock
import yaml
from toxicbuild.slave import build, managers, plugins
from tests.unit.slave import TEST_DATA_DIR
from tests import async_test


class BuilderTest(TestCase):

    @mock.patch.object(managers, 'get_toxicbuildconf_yaml', mock.MagicMock())
    def setUp(self):
        super().setUp()
        protocol = mock.MagicMock()

        async def s(*a, **kw):
            pass

        protocol.send_response = s

        manager = managers.BuildManager(protocol, 'repo-id', 'git@repo.git',
                                        'git', 'master', 'v0.1')
        toxicconf = os.path.join(TEST_DATA_DIR, 'toxicbuild.yml')
        with open(toxicconf) as fd:
            conf = fd.read()

        toxicconf = yaml.safe_load(conf)

        managers.get_toxicbuildconf_yaml.return_value = toxicconf

        self.builder = build.Builder(manager, {'name': 'builder1',
                                               'steps': []}, '.')

    @async_test
    async def test_build_success(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='echo "uhu!"')
        self.builder.steps = [s1, s2]
        self.builder._copy_workdir = AsyncMock(
            spec=self.builder._copy_workdir)
        self.builder._remove_tmp_dir = AsyncMock()
        self.builder._get_tmp_dir = mock.Mock(return_value='.')

        build_info = await self.builder.build()
        self.assertEqual(build_info['status'], 'success')
        self.assertIn('total_time', build_info['steps'][0].keys())

    @async_test
    async def test_build_fail(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='exit 1')
        s3 = build.BuildStep(name='s3', command='echo "oi"')
        self.builder._copy_workdir = AsyncMock(
            spec=self.builder._copy_workdir)
        self.builder._remove_tmp_dir = AsyncMock()
        self.builder._get_tmp_dir = mock.Mock(return_value='.')
        self.builder.steps = [s1, s2, s3]
        build_info = await self.builder.build()
        self.assertEqual(build_info['status'], 'fail')

    @async_test
    async def test_build_fail_stop_on_fail(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='exit 1', stop_on_fail=True)
        s3 = build.BuildStep(name='s3', command='echo "oi"')
        self.builder.steps = [s1, s2, s3]
        self.builder._copy_workdir = AsyncMock(
            spec=self.builder._copy_workdir)

        self.builder._remove_tmp_dir = AsyncMock()
        self.builder._get_tmp_dir = mock.Mock(return_value='.')

        build_info = await self.builder.build()
        self.assertEqual(build_info['status'], 'fail')
        self.assertEqual(len(build_info['steps']), 2)

    @mock.patch.object(build, 'exec_cmd', AsyncMock(
        side_effect=asyncio.TimeoutError))
    @async_test
    async def test_build_fail_stop_on_fail_exception(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='exit 1', stop_on_fail=True)
        s3 = build.BuildStep(name='s3', command='echo "oi"')
        self.builder.steps = [s1, s2, s3]
        self.builder._copy_workdir = AsyncMock(
            spec=self.builder._copy_workdir)

        self.builder._remove_tmp_dir = AsyncMock()
        self.builder._get_tmp_dir = mock.Mock(return_value='.')

        build_info = await self.builder.build()
        self.assertEqual(build_info['status'], 'exception')
        self.assertEqual(len(build_info['steps']), 2)

    @async_test
    async def test_send_step_output_info_step_index(self):
        step_info = {'uuid': 'some-uuid'}

        send_mock = mock.Mock()

        async def send_info(msg):
            send_mock(msg)

        self.builder.manager.send_info = send_info
        self.builder._current_step_output_index = 1
        await self.builder._send_step_output_info(step_info,
                                                  0, 'some line' * 1024)
        self.assertTrue(send_mock.called)

    @async_test
    async def test_send_step_output_info(self):
        step_info = {'uuid': 'some-uuid'}

        send_mock = mock.Mock()

        async def send_info(msg):
            send_mock(msg)

        self.builder.manager.send_info = send_info
        await self.builder._send_step_output_info(step_info,
                                                  0, 'some line' * 1024)
        self.assertTrue(send_mock.called)

    @async_test
    async def test_send_step_output_info_short(self):
        step_info = {'uuid': 'some-uuid'}

        send_mock = mock.Mock()

        async def send_info(msg):
            send_mock(msg)

        self.builder.STEP_OUTPUT_BUFF_LEN = 512
        self.builder.manager.send_info = send_info
        await self.builder._send_step_output_info(step_info,
                                                  0, 'some line')
        self.assertFalse(send_mock.called)

    @async_test
    async def test_get_env_vars(self):
        pconfig = [{'name': 'python-venv', 'pyversion': '/usr/bin/python3.4'}]
        self.builder.conf['plugins'] = pconfig
        self.builder.plugins = self.builder._load_plugins()
        expected = {
            'PATH': '$PWD/.././python-venv/venv-usrbinpython3.4/bin:PATH'}
        returned = self.builder._get_env_vars()

        self.assertEqual(expected, returned)

    @async_test
    async def test_get_envvar_with_builder_envvars(self):
        pconfig = [{'name': 'python-venv', 'pyversion': '/usr/bin/python3.4'}]
        self.builder.conf['plugins'] = pconfig
        self.builder.plugins = self.builder._load_plugins()
        self.builder.envvars = {'VAR1': 'someval'}
        expected = {
            'PATH': '$PWD/.././python-venv/venv-usrbinpython3.4/bin:PATH',
            'VAR1': 'someval'}
        returned = self.builder._get_env_vars()
        self.assertEqual(expected, returned)

    def test_get_tmp_dir(self):
        expected = '{}-{}'.format(os.path.abspath(
            self.builder.workdir), self.builder.name)
        self.assertEqual(expected, self.builder._get_tmp_dir())

    @mock.patch.object(build, 'exec_cmd', AsyncMock())
    @async_test
    async def test_copy_workdir(self):
        await self.builder._copy_workdir()
        self.assertEqual(len(build.exec_cmd.call_args_list), 2)
        expected0 = 'mkdir -p {}'.format(self.builder._get_tmp_dir())
        expected1 = 'cp -R {}/* {}'.format(self.builder.workdir,
                                           self.builder._get_tmp_dir())
        called0 = build.exec_cmd.call_args_list[0][0][0]
        called1 = build.exec_cmd.call_args_list[1][0][0]
        self.assertEqual(expected0, called0)
        self.assertEqual(expected1, called1)

    @mock.patch.object(build, 'exec_cmd', AsyncMock())
    @async_test
    async def test_remove_dir(self):
        expected = 'rm -rf {}'.format(self.builder._get_tmp_dir())
        await self.builder._remove_tmp_dir()
        called = build.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @async_test
    async def test_test_aenter(self):
        self.builder._copy_workdir = AsyncMock()
        self.builder._remove_tmp_dir = AsyncMock()
        async with self.builder._run_in_build_env():
            self.assertTrue(self.builder._copy_workdir.called)

    @async_test
    async def test_aexit(self):
        self.builder._copy_workdir = AsyncMock()
        self.builder._remove_tmp_dir = AsyncMock()
        async with self.builder._run_in_build_env():
            pass

        self.assertTrue(self.builder._remove_tmp_dir.called)

    @async_test
    async def test_aexit_no_remove(self):
        self.builder.remove_env = False
        self.builder._copy_workdir = AsyncMock()
        self.builder._remove_tmp_dir = AsyncMock()
        async with self.builder._run_in_build_env():
            pass

        self.assertFalse(self.builder._remove_tmp_dir.called)

    def test_load_plugins(self):
        plugins_conf = [{'name': 'apt-install',
                         'packages': ['some-package', 'other']}]
        self.builder.conf['plugins'] = plugins_conf
        returned = self.builder._load_plugins()

        self.assertEqual(type(returned[0]), plugins.AptInstallPlugin)

    def test_load_plugins_no_name(self):
        plugins_conf = [{'pyversion': '/usr/bin/python3.4'}]
        self.builder.conf['plugins'] = plugins_conf
        with self.assertRaises(build.BadPluginConfig):
            self.builder._load_plugins()

    def test_get_steps(self):
        self.builder.conf['steps'] = ['ls', {'name': 'other',
                                             'command': 'cmd2'}]
        steps = self.builder._get_steps()
        self.assertEqual(len(steps), 2)


class BuildStepTest(TestCase):

    @async_test
    async def test_step_success(self):
        step = build.BuildStep(name='test', command='ls')
        status = await step.execute(cwd='.')
        self.assertEqual(status['status'], 'success')

    @async_test
    async def test_step_fail(self):
        step = build.BuildStep(name='test', command='lsz')
        status = await step.execute(cwd='.')
        self.assertEqual(status['status'], 'fail')

    @async_test
    async def test_step_warning_on_fail(self):
        step = build.BuildStep(
            name='test', command='lsz', warning_on_fail=True)
        status = await step.execute(cwd='.')
        self.assertEqual(status['status'], 'warning')

    def test_equal_with_other_object(self):
        """ Ensure that one step is not equal something that is not a step"""

        step = build.BuildStep(name='test', command='lsz')
        self.assertNotEqual(step, {})

    @async_test
    async def test_step_timeout(self):
        step = build.BuildStep(name='test', command='sleep 1', timeout=0.5)
        status = await step.execute(cwd='.')
        self.assertEqual(status['status'], 'exception')
        await asyncio.sleep(1)

    @async_test
    async def test_step_timeout_warning_on_fail(self):
        step = build.BuildStep(name='test', command='sleep 1', timeout=0.5,
                               warning_on_fail=True)
        status = await step.execute(cwd='.')
        self.assertEqual(status['status'], 'warning')
        await asyncio.sleep(1)
