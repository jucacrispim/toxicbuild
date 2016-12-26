# -*- coding: utf-8 -*-

# Copyright 2015, 2016 Juca Crispim <juca@poraodojuca.net>

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
import os
from unittest import mock, TestCase
import tornado
from toxicbuild.core.utils import load_module_from_file
from toxicbuild.slave import build, managers
from tests.unit.slave import TEST_DATA_DIR
from tests import async_test


class BuilderTest(TestCase):

    @mock.patch.object(managers, 'get_toxicbuildconf', mock.MagicMock())
    def setUp(self):
        super().setUp()
        protocol = mock.MagicMock()

        @asyncio.coroutine
        def s(*a, **kw):
            pass

        protocol.send_response = s

        manager = managers.BuildManager(protocol, 'git@repo.git', 'git',
                                        'master', 'v0.1')
        toxicconf = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
        toxicconf = load_module_from_file(toxicconf)

        managers.get_toxicbuildconf.return_value = toxicconf

        self.builder = build.Builder(manager, 'builder1', '.')

    @async_test
    def test_build_success(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='echo "uhu!"')
        self.builder.steps = [s1, s2]

        build_info = yield from self.builder.build()
        self.assertEqual(build_info['status'], 'success')

    @async_test
    def test_build_fail(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='exit 1')
        s3 = build.BuildStep(name='s3', command='echo "oi"')
        self.builder.steps = [s1, s2, s3]

        build_info = yield from self.builder.build()
        self.assertEqual(build_info['status'], 'fail')

    @async_test
    def test_build_fail_stop_on_fail(self):
        s1 = build.BuildStep(name='s1', command='ls')
        s2 = build.BuildStep(name='s2', command='exit 1', stop_on_fail=True)
        s3 = build.BuildStep(name='s3', command='echo "oi"')
        self.builder.steps = [s1, s2, s3]

        build_info = yield from self.builder.build()
        self.assertEqual(build_info['status'], 'fail')
        self.assertEqual(len(build_info['steps']), 2)

    @async_test
    def test_send_step_output_info(self):
        step_info = {'uuid': 'some-uuid'}

        send_mock = mock.Mock()

        @asyncio.coroutine
        def send_info(msg):
            send_mock(msg)

        self.builder.manager.send_info = send_info
        yield from self.builder._send_step_output_info(step_info,
                                                       0, 'some line')
        self.assertTrue(send_mock.called)

    def test_get_env_vars(self):
        pconfig = [{'name': 'python-venv', 'pyversion': '/usr/bin/python3.4'}]
        self.builder.plugins = self.builder.manager._load_plugins(pconfig)
        expected = {'PATH': 'venv-usrbinpython3.4/bin:PATH'}
        returned = self.builder._get_env_vars()

        self.assertEqual(expected, returned)

    def test_get_envvar_with_builder_envvars(self):
        pconfig = [{'name': 'python-venv', 'pyversion': '/usr/bin/python3.4'}]
        self.builder.plugins = self.builder.manager._load_plugins(pconfig)
        self.builder.envvars = {'VAR1': 'someval'}
        expected = {'PATH': 'venv-usrbinpython3.4/bin:PATH',
                    'VAR1': 'someval'}
        returned = self.builder._get_env_vars()
        self.assertEqual(expected, returned)


class BuildStepTest(TestCase):

    @async_test
    def test_step_success(self):
        step = build.BuildStep(name='test', command='ls')
        status = yield from step.execute(cwd='.')
        self.assertEqual(status['status'], 'success')

    @async_test
    def test_step_fail(self):
        step = build.BuildStep(name='test', command='lsz')
        status = yield from step.execute(cwd='.')
        self.assertEqual(status['status'], 'fail')

    @async_test
    def test_step_warning_on_fail(self):
        step = build.BuildStep(
            name='test', command='lsz', warning_on_fail=True)
        status = yield from step.execute(cwd='.')
        self.assertEqual(status['status'], 'warning')

    def test_equal_with_other_object(self):
        """ Ensure that one step is not equal something that is not a step"""

        step = build.BuildStep(name='test', command='lsz')
        self.assertNotEqual(step, {})

    @async_test
    def test_step_timeout(self):
        step = build.BuildStep(name='test', command='sleep 1', timeout=1)
        status = yield from step.execute(cwd='.')
        self.assertEqual(status['status'], 'exception')
        yield from asyncio.sleep(1)
