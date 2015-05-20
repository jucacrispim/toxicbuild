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


class BuildTest(AsyncTestCase):

    def tearDown(self):
        build.Build.drop_collection()
        build.Builder.drop_collection()
        build.Slave.drop_collection()
        repositories.RepositoryRevision.drop_collection()
        repositories.Repository.drop_collection()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_get_parallels(self):
        yield from self._create_test_data()

        build = self.builds[0]
        parallels = yield from build.get_parallels()

        self.assertEqual(len(parallels), 1)

    @asyncio.coroutine
    def _create_test_data(self):
        self.slave = yield from build.Slave.create(name='slave',
                                                   host='localhost',
                                                   port=7777)
        self.repo = repositories.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        yield self.repo.save()

        self.revision = repositories.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now()
        )

        yield self.revision.save()

        self.builders = []
        for i in range(2):
            builder = build.Builder(repository=self.repo,
                                    name='builder-%s' % i)
            yield builder.save()
            self.builders.append(builder)

        self.builds = []
        for i in range(3):
            try:
                builder = self.builders[i]
            except IndexError:
                builder = self.builders[0]

            binst = build.Build(repository=self.repo, slave=self.slave,
                                branch='master', named_tree='v0.1',
                                builder=builder)

            yield binst.save()

            self.builds.append(binst)


@mock.patch.object(build, 'build_started', mock.Mock())
@mock.patch.object(build, 'build_finished', mock.Mock())
@mock.patch.object(build, 'step_started', mock.Mock())
@mock.patch.object(build, 'step_finished', mock.Mock())
class SlaveTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.slave = build.Slave(name='slave', host='127.0.0.1', port=7777)

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
        slave = yield from build.Slave.create(name='name',
                                              host='somewhere.net', port=7777)
        self.assertTrue(slave.id)

    @gen_test
    def test_get(self):
        slave = yield from build.Slave.create(name='name',
                                              host='somewhere.net', port=7777)
        slave_id = slave.id

        slave = yield from build.Slave.get(name='name', host='somewhere.net',
                                           port=7777)

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

        self.assertEqual(builders, [self.builder, self.other_builder])

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
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        yield self.repo.save()

        self.revision = repositories.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now()
        )

        yield self.revision.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        yield self.builder.save()
        self.other_builder = build.Builder(repository=self.repo,
                                           name='builder-2')
        yield self.other_builder.save()
        yield self.builder.save()

        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder)

        self.build.save()


class BuildManagerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()

        repo = mock.MagicMock()
        repo.__self__ = repo
        repo.__func__ = lambda: None
        self.manager = build.BuildManager(repo)

    def tearDown(self):
        build.Slave.drop_collection()
        build.Build.drop_collection()
        repositories.RepositoryRevision.drop_collection()
        repositories.Repository.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_add_builds(self):
        yield from self._create_test_data()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        @asyncio.coroutine
        def lb(revision):
            return ['builder-1', 'builder-2']

        self.slave.list_builders = lb

        yield from self.manager.add_builds(self.revision)

        self.assertEqual(len(self.manager._queues[self.slave]), 2)

    @gen_test
    def test_get_builders(self):
        yield from self._create_test_data()

        @asyncio.coroutine
        def lb(revision):
            return ['builder-1', 'builder-2']

        self.slave.list_builders = lb

        self.manager._execute_builds = mock.MagicMock()

        builders = yield from self.manager.get_builders(self.slave,
                                                        self.revision)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 2)

    @gen_test
    def test_execute_build(self):
        yield from self._create_test_data()

        self.manager._execute_in_parallel = mock.MagicMock()
        self.manager._queues[self.slave].extend(
            [self.build, self.consumed_build])
        yield from self.manager._execute_builds(self.slave)
        called_args = self.manager._execute_in_parallel.call_args[0]

        self.assertEqual(len(called_args), 2)

    @gen_test
    def test_execute_in_parallel(self):
        yield from self._create_test_data()

        builds = [self.build, self.consumed_build]

        self.slave.build = asyncio.coroutine(lambda x: None)

        fs = yield from self.manager._execute_in_parallel(self.slave, builds)

        for f in fs:
            self.assertTrue(f.done())

    @asyncio.coroutine
    def _create_test_data(self):
        self.slave = build.Slave(host='127.0.0.1', port=7777, name='slave')
        self.slave.build = asyncio.coroutine(lambda x: None)
        yield self.slave.save()
        self.repo = repositories.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

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
        yield self.build.save()
        self.consumed_build = build.Build(repository=self.repo,
                                          slave=self.slave, branch='master',
                                          named_tree='v0.1',
                                          builder=self.builder,
                                          status='running')
        yield self.consumed_build.save()
