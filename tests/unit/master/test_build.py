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
from toxicbuild.core.utils import now
from toxicbuild.master import build, repository, slave


class BuildStepTest(AsyncTestCase):

    def test_to_dict(self):
        bs = build.BuildStep(name='bla', command='ls', status='fail',
                             started=now(), finished=now())

        objdict = bs.to_dict()
        self.assertTrue(objdict['started'])

    def test_to_json(self):
        bs = build.BuildStep(name='bla',
                             command='ls',
                             status='pending')
        bsd = build.json.loads(bs.to_json())
        self.assertIn('finished', bsd.keys())


class BuildTest(AsyncTestCase):

    def tearDown(self):
        build.Build.drop_collection()
        build.Builder.drop_collection()
        slave.Slave.drop_collection()
        repository.RepositoryRevision.drop_collection()
        repository.Repository.drop_collection()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def test_to_json(self):
        bs = build.BuildStep(name='bla',
                             command='ls',
                             status='pending')
        b = build.Build()
        b.steps.append(bs)
        bd = build.json.loads(b.to_json())
        self.assertIn('finished', bd['steps'][0].keys())

    @gen_test
    def test_get_parallels(self):
        yield from self._create_test_data()

        build = self.builds[0]
        parallels = yield from build.get_parallels()

        self.assertEqual(len(parallels), 1)

    @asyncio.coroutine
    def _create_test_data(self):
        self.slave = yield from slave.Slave.create(name='slave',
                                                   host='localhost',
                                                   port=7777)
        self.repo = repository.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        yield self.repo.save()

        self.revision = repository.RepositoryRevision(
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
                                builder=builder, number=i)

            yield binst.save()

            self.builds.append(binst)


class BuildManagerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()

        repo = mock.MagicMock()
        repo.__self__ = repo
        repo.__func__ = lambda: None
        self.manager = build.BuildManager(repo)

    @gen_test
    def tearDown(self):
        yield slave.Slave.drop_collection()
        yield build.Build.drop_collection()
        yield build.Builder.drop_collection()
        yield repository.RepositoryRevision.drop_collection()
        yield repository.Repository.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_add_builds(self):
        yield from self._create_test_data()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        @asyncio.coroutine
        def lb(branch, slave):
            return [self.builder]

        self.manager.get_builders = lb

        yield from self.manager.add_builds([self.revision])

        self.assertEqual(len(self.manager._build_queues[self.slave.name]), 1)

    @mock.patch.object(build, 'get_toxicbuildconf', mock.Mock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(return_value=['builder-0', 'builder-1']))
    @gen_test
    def test_get_builders(self):
        yield from self._create_test_data()
        self.manager.repository = self.repo
        self.manager.repository.poller.vcs.checkout = mock.MagicMock()

        builders = yield from self.manager.get_builders(self.slave,
                                                        self.revision)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 2)

    @mock.patch.object(build, 'get_toxicbuildconf', mock.Mock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(side_effect=AttributeError))
    @mock.patch.object(build, 'log', mock.Mock())
    @gen_test
    def test_get_builders_with_bad_toxicbuildconf(self):
        yield from self._create_test_data()
        self.manager.repository = self.repo
        self.manager.repository.poller.vcs.checkout = mock.MagicMock()

        builders = yield from self.manager.get_builders(self.slave,
                                                        self.revision)
        self.assertFalse(builders)
        self.assertTrue(build.log.called)

    @gen_test
    def test_execute_build(self):
        yield from self._create_test_data()

        self.manager._execute_in_parallel = mock.MagicMock()
        self.manager._build_queues[self.slave.name].extend(
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

    @gen_test
    def test_get_next_build_number_without_build(self):
        yield from self._create_test_data()
        yield from build.to_asyncio_future(build.Build.drop_collection())
        number = yield from self.manager._get_next_build_number(self.builder)
        self.assertEqual(number, 0)

    @gen_test
    def test_get_next_build_number_with_build(self):
        yield from self._create_test_data()
        number = yield from self.manager._get_next_build_number(self.builder)
        self.assertEqual(number, 2)

    @gen_test
    def test_add_builds_from_signal(self):
        # ensures that builds are added when revision_added signal is sent.

        yield from self._create_test_data()
        yield build.Build.drop_collection()
        self.repo.build_manager.add_builds = mock.MagicMock()
        ret = self.repo.poller.notify_change(*[self.revision])
        futures = [r[1] for r in ret]
        yield from asyncio.gather(*futures)
        self.assertTrue(self.repo.build_manager.add_builds.called)

    @asyncio.coroutine
    def _create_test_data(self):
        self.slave = slave.Slave(host='127.0.0.1', port=7777, name='slave')
        self.slave.build = asyncio.coroutine(lambda x: None)
        yield self.slave.save()
        self.repo = repository.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        yield self.repo.save()

        self.revision = repository.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now()
        )

        yield self.revision.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        yield self.builder.save()
        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder, number=0)
        yield self.build.save()
        self.consumed_build = build.Build(repository=self.repo,
                                          slave=self.slave, branch='master',
                                          named_tree='v0.1',
                                          builder=self.builder,
                                          status='running', number=1)
        yield self.consumed_build.save()


class BuilderTest(AsyncTestCase):

    @gen_test
    def tearDown(self):
        yield build.Builder.drop_collection()
        yield repository.Repository.drop_collection()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_create(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()

        builder = yield from build.Builder.create(repository=repo, name='b1')
        self.assertTrue(builder.id)

    @gen_test
    def test_get(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()
        builder = yield from build.Builder.create(repository=repo, name='b1')

        returned = yield from build.Builder.get(repository=repo, name='b1')

        self.assertEqual(returned, builder)

    @mock.patch.object(build.Builder, 'create', mock.MagicMock())
    @gen_test
    def test_get_or_create_with_create(self):

        yield from build.Builder.get_or_create(name='bla')

        self.assertTrue(build.Builder.create.called)

    @mock.patch.object(build.Builder, 'create', mock.MagicMock())
    @gen_test
    def test_get_or_create_with_get(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()
        builder = yield from build.Builder.create(repository=repo, name='b1')

        returned = yield from build.Builder.get_or_create(
            repository=repo, name='b1')

        self.assertEqual(returned, builder)

    @gen_test
    def test_get_status_without_build(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()
        builder = yield from build.Builder.create(repository=repo, name='b1')
        status = yield from builder.get_status()

        self.assertEqual(status, 'idle')

    @gen_test
    def test_get_status(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234)
        yield slave_inst.save()
        builder = yield from build.Builder.create(repository=repo, name='b1')
        buildinst = build.Build(repository=repo, slave=slave_inst,
                                branch='master', named_tree='v0.1',
                                builder=builder, number=0,
                                status='success', started=now())
        yield buildinst.save()
        status = yield from builder.get_status()

        self.assertEqual(status, 'success')
