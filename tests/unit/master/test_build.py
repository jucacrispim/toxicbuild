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
import datetime
from unittest import mock
import tornado
from tornado.testing import AsyncTestCase, gen_test
import toxicbuild
from toxicbuild.master import build, repositories


@mock.patch.object(build, 'log', mock.Mock())
@mock.patch.object(build, 'build_started', mock.Mock())
@mock.patch.object(build, 'build_finished', mock.Mock())
@mock.patch.object(build, 'step_started', mock.Mock())
@mock.patch.object(build, 'step_finished', mock.Mock())
class SlaveTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.slave = build.Slave(host='127.0.0.1', port=7777)

    def tearDown(self):
        build.Slave.drop_collection()
        build.Build.drop_collection()
        build.Builder.drop_collection()
        repositories.RepositoryRevision.drop_collection()
        repositories.Repository.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_create(self):
        slave = yield from build.Slave.create('somewhere.net', 7777)
        self.assertTrue(slave.id)

    @gen_test
    def test_get(self):
        slave = yield from build.Slave.create('somewhere.net', 7777)
        slave_id = slave.id

        slave = yield from build.Slave.get('somewhere.net', 7777)

        self.assertEqual(slave_id, slave.id)

    @mock.patch.object(toxicbuild.master.client.asyncio, 'open_connection',
                       mock.Mock())
    @gen_test
    def test_get_client(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return [mock.MagicMock(), mock.MagicMock()]

        toxicbuild.master.client.asyncio.open_connection = oc
        client = yield from self.slave.get_client()
        self.assertTrue(client._connected)

    @gen_test
    def test_healthcheck(self):

        @asyncio.coroutine
        def gc():
            client = mock.MagicMock()

            @asyncio.coroutine
            def hc():  # x no pé!
                return True

            client.__enter__.return_value.healthcheck = hc
            return client

        self.slave.get_client = gc

        yield from self.slave.healthcheck()

        self.assertTrue(self.slave.is_alive)

    @gen_test
    def test_list_builders(self):
        yield from self._create_test_data()

        @asyncio.coroutine
        def gc():
            client = mock.MagicMock()

            @asyncio.coroutine
            def lb(repo_url, vcs_type, branch, named_tree):
                return ['builder-1', 'builder-2']

            client.__enter__.return_value.list_builders = lb
            return client

        self.slave.get_client = gc

        builders = yield from self.slave.list_builders(self.revision)
        self.assertEqual(builders, ['builder-1', 'builder-2'])

    @gen_test
    def test_build(self):
        yield from self._create_test_data()

        @asyncio.coroutine
        def gc():
            client = mock.MagicMock()

            @asyncio.coroutine
            def b(repo_url, vcs_type, branch, named_tree, builder_name):
                yield {'status': 'running', 'cmd': 'ls', 'name': 'list_files',
                       'output': ''}

                yield {'status': 'success', 'cmd': 'ls', 'name': 'list_files',
                       'output': 'somefile.txt\n'}

                yield {'status': 'success', 'total_steps': 1,
                       'steps': [{'status': 'success', 'cmd': 'ls',
                                  'name': 'list_files',
                                  'output': 'somefile.txt\n'}]}

            client.__enter__.return_value.build = b
            return client

        self.slave.get_client = gc
        build = yield from self.slave.build(self.build)

        self.assertEqual(build.status, 'success')
        self.assertEqual(len(build.steps), 1)
        self.assertTrue(build.finished)

    @gen_test
    def test_get_step_new(self):
        yield from self._create_test_data()

        step = yield from self.slave._get_step(self.build, 'ls', 'run ls',
                                               'running', '')
        self.assertEqual(step, self.build.steps[0])

    @gen_test
    def test_get_step(self):
        yield from self._create_test_data()

        step = yield from self.slave._get_step(self.build, 'ls', 'run ls',
                                               'running', '')
        step_cmd = step.command

        step = yield from self.slave._get_step(self.build, 'ls', 'run ls',
                                               'success', 'somefile.txt\n')

        self.assertEqual(step.command, step_cmd)
        self.assertEqual(step.status, 'success')
        self.assertEqual(len(self.build.steps), 1)

    @asyncio.coroutine
    def _create_test_data(self):
        yield self.slave.save()
        self.repo = repositories.Repository(
            url='git@somewhere', update_seconds=300, vcs_type='git',
            slaves=[self.slave])

        yield self.repo.save()

        self.revision = repositories.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now()
        )

        yield self.revision.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        yield self.builder.save()

        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder)

        self.build.save()


class BuildManagerTest(AsyncTestCase):

    def tearDown(self):
        build.Slave.drop_collection()
        build.Build.drop_collection()
        repositories.RepositoryRevision.drop_collection()
        repositories.Repository.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @mock.patch.object(build, 'build_added', mock.Mock())
    @gen_test
    def test_add_builds(self):
        yield from self._create_test_data()

        @asyncio.coroutine
        def lb(revision):
            return ['builder-1', 'builder-2']

        self.slave.list_builders = lb

        yield from build.BuildManager.add_builds(mock.Mock(), self.revision)

        self.assertEqual(len(build.build_added.send.call_args_list), 2)

    @gen_test
    def test_execute_build(self):
        yield from self._create_test_data()
        self.BUILDED = False

        @asyncio.coroutine
        def b(build):
            self.BUILDED = True

        self.slave.build = b

        # taking the return and yield from coro are only for
        # tests purposes.
        coro = yield from build.BuildManager.execute_build(mock.Mock(),
                                                           self.build)

        yield from coro

        self.assertTrue(self.BUILDED)

    @asyncio.coroutine
    def _create_test_data(self):
        self.slave = build.Slave(host='127.0.0.1', port=7777)
        yield self.slave.save()
        self.repo = repositories.Repository(
            url='git@somewhere', update_seconds=300, vcs_type='git',
            slaves=[self.slave])

        yield self.repo.save()

        self.revision = repositories.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now()
        )

        yield self.revision.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        yield self.builder.save()
        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder)
