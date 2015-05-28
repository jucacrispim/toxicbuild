# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
import mock
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core.utils import load_module_from_file
from toxicbuild.slave import build
from tests.unit.slave import TEST_DATA_DIR


TOXICCONF = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
TOXICCONF = load_module_from_file(TOXICCONF)


@mock.patch.object(build, 'load_module_from_file',
                   mock.MagicMock(return_value=TOXICCONF))
class BuilderManagerTest(AsyncTestCase):

    @mock.patch.object(build, 'get_vcs', mock.MagicMock())
    def setUp(self):
        super().setUp()
        protocol = mock.MagicMock()

        @asyncio.coroutine
        def s(*a, **kw):
            pass

        protocol.send_response = s

        self.manager = build.BuildManager(protocol, 'git@repo.git', 'git',
                                          'master', 'v0.1')

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_update_and_checkout_with_clone(self):
        self.manager.vcs.workdir_exists.return_value = False

        yield from self.manager.update_and_checkout()

        self.assertTrue(self.manager.vcs.clone.called)
        self.assertTrue(self.manager.vcs.checkout.called)
        self.assertTrue(self.manager.vcs.pull.called)

    def test_list_builders(self):
        expected = ['builder1', 'builder2']
        returned = self.manager.list_builders()

        self.assertEqual(returned, expected)

    def test_load_builder(self):
        builder = self.manager.load_builder('builder1')
        self.assertEqual(len(builder.steps), 2)

    def test_load_builder_with_not_found(self):
        with self.assertRaises(build.BuilderNotFound):
            builder = self.manager.load_builder('builder3')
            del builder


class BuilderTest(AsyncTestCase):

    @mock.patch.object(build, 'load_module_from_file', mock.MagicMock())
    def setUp(self):
        super().setUp()
        protocol = mock.MagicMock()

        @asyncio.coroutine
        def s(*a, **kw):
            pass

        protocol.send_response = s

        manager = build.BuildManager(protocol, 'git@repo.git', 'git',
                                     'master', 'v0.1')
        toxicconf = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
        toxicconf = load_module_from_file(toxicconf)

        build.load_module_from_file.return_value = toxicconf

        self.builder = build.Builder(manager, 'builder1', '.')

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_build_success(self):
        s1 = build.BuildStep(name='s1', cmd='ls')
        s2 = build.BuildStep(name='s2', cmd='echo "uhu!"')
        self.builder.steps = [s1, s2]

        build_info = yield from self.builder.build()
        self.assertEqual(build_info['status'], 'success')

    @gen_test
    def test_build_fail(self):
        s1 = build.BuildStep(name='s1', cmd='ls')
        s2 = build.BuildStep(name='s2', cmd='exit 1')
        self.builder.steps = [s1, s2]

        build_info = yield from self.builder.build()
        self.assertEqual(build_info['status'], 'fail')


class BuildStepTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_step_success(self):
        step = build.BuildStep(name='test', cmd='ls')
        status = yield from step.execute()
        self.assertEqual(status['status'], 'success')

    @gen_test
    def test_step_fail(self):
        step = build.BuildStep(name='test', cmd='lsz')
        status = yield from step.execute()
        self.assertEqual(status['status'], 'fail')
