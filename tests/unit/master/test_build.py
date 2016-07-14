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

    @gen_test
    def tearDown(self):
        yield build.BuildSet.drop_collection()
        yield build.Builder.drop_collection()
        yield slave.Slave.drop_collection()
        yield repository.RepositoryRevision.drop_collection()
        yield repository.Repository.drop_collection()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_to_json(self):
        yield self._create_test_data()
        bs = build.BuildStep(name='bla',
                             command='ls',
                             status='pending')
        self.buildset.builds[0].steps.append(bs)
        bd = build.json.loads((yield from self.buildset.builds[0].to_json()))
        self.assertIn('finished', bd['steps'][0].keys())
        self.assertTrue(bd['builder']['id'])

    @gen_test
    def test_update(self):
        yield self._create_test_data()
        b = self.buildset.builds[0]
        b.status = 'fail'
        yield from b.update()

        buildset = yield build.BuildSet.objects.get(id=self.buildset.id)
        self.assertEqual(buildset.builds[0].status, 'fail')

    @gen_test
    def test_update_without_save(self):
        yield self._create_test_data()

        b = build.Build(branch='master', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')

        with self.assertRaises(build.DBError):
            yield from b.update()

    @tornado.gen.coroutine
    def _create_test_data(self):
        self.repo = repository.Repository(name='bla', url='git@bla.com')
        yield self.repo.save()
        self.slave = slave.Slave(name='sla', host='localhost', port=1234)
        yield self.slave.save()
        self.builder = build.Builder(repository=self.repo, name='builder-bla')
        yield self.builder.save()
        b = build.Build(branch='master', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        rev = repository.RepositoryRevision(commit='saçfijf',
                                            commit_date=now(),
                                            repository=self.repo,
                                            branch='master')
        yield rev.save()

        self.buildset = build.BuildSet(repository=self.repo,
                                       revision=rev,
                                       commit='dsasdfdas',
                                       commit_date=now,
                                       builds=[b])
        yield self.buildset.save()


class BuildSetTest(AsyncTestCase):

    @gen_test
    def tearDown(self):
        yield repository.Repository.drop_collection()
        yield slave.Slave.drop_collection()
        yield build.BuildSet.drop_collection()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_create(self):
        yield self._create_test_data()
        buildset = yield from build.BuildSet.create(self.repo, self.rev)
        self.assertTrue(buildset.commit)
        self.assertTrue(buildset.id)

    @gen_test
    def test_create_without_save(self):
        yield self._create_test_data()
        buildset = yield from build.BuildSet.create(self.repo, self.rev,
                                                    save=False)
        self.assertFalse(buildset.id)

    @gen_test
    def test_to_dict(self):
        yield self._create_test_data()
        objdict = yield from self.buildset.to_dict()
        self.assertEqual(len(objdict['builds']), 1)

    @gen_test
    def test_to_json(self):
        yield self._create_test_data()

        objdict = build.json.loads((yield from self.buildset.to_json()))
        self.assertTrue(objdict['id'])

    @gen_test
    def test_status_running(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']
        for i in range(5):
            build_inst = build.Build(status=statuses[i])
            buildset.builds.append(build_inst)

        status = buildset.get_status()
        self.assertEqual(status, 'running')

    @gen_test
    def test_status_exception(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']

        for i in range(5):
            if i > 0:
                build_inst = build.Build(status=statuses[i])
                buildset.builds.append(build_inst)

        status = buildset.get_status()
        self.assertEqual(status, 'exception')

    @gen_test
    def test_status_fail(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']
        for i in range(5):
            if i > 1:
                build_inst = build.Build(status=statuses[i])
                buildset.builds.append(build_inst)

        status = buildset.get_status()
        self.assertEqual(status, 'fail')

    def test_get_pending_builds(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']

        for i in range(6):
            build_inst = build.Build(status=statuses[i])
            buildset.builds.append(build_inst)

        pending = buildset.get_pending_builds()
        self.assertEqual(len(pending), 1)

    @gen_test
    def test_get_builds_for_branch(self):
        yield self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)

        builds = yield from self.buildset.get_builds_for(branch='other')
        self.assertEqual(len(builds), 1)

    @gen_test
    def test_get_builds_for_builder(self):
        yield self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)

        builds = yield from self.buildset.get_builds_for(builder=self.builder)
        self.assertEqual(len(builds), 2)

    @gen_test
    def test_get_builds_for_builder_and_branch(self):
        yield self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)

        builds = yield from self.buildset.get_builds_for(builder=self.builder,
                                                         branch='master')
        self.assertEqual(len(builds), 1)

    @tornado.gen.coroutine
    def _create_test_data(self):
        self.repo = repository.Repository(name='bla', url='git@bla.com')
        yield self.repo.save()
        self.slave = slave.Slave(name='sla', host='localhost', port=1234)
        yield self.slave.save()
        self.builder = build.Builder(repository=self.repo, name='builder-bla')
        yield self.builder.save()
        self.build = build.Build(branch='master', builder=self.builder,
                                 repository=self.repo, slave=self.slave,
                                 named_tree='v0.1')
        self.rev = repository.RepositoryRevision(commit='saçfijf',
                                                 commit_date=now(),
                                                 repository=self.repo,
                                                 branch='master')
        yield self.rev.save()
        self.buildset = build.BuildSet(repository=self.repo,
                                       revision=self.rev,
                                       commit='alsdfjçasdfj',
                                       commit_date=now,
                                       builds=[self.build])
        yield self.buildset.save()


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
        yield build.BuildSet.drop_collection()
        yield build.Builder.drop_collection()
        yield repository.RepositoryRevision.drop_collection()
        yield repository.Repository.drop_collection()
        yield repository.Slave.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_add_builds_for_slave(self):
        yield from self._create_test_data()
        b = build.Builder()
        b.repository = self.repo
        b.name = 'blabla'
        yield b.save()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        yield from self.manager.add_builds_for_slave(self.buildset, self.slave,
                                                     [b, self.builder])
        self.assertEqual(len(self.manager._build_queues[self.slave.name]), 1)
        buildset = self.manager._build_queues[self.slave.name][0]
        # It already has two builds from _create_test_data and more two
        # from .add_builds_for_slave
        self.assertEqual(len(buildset.builds), 4)

    @gen_test
    def test_add_builds(self):
        yield from self._create_test_data()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        @asyncio.coroutine
        def gb(branch, slave):
            return [self.builder]

        self.manager.get_builders = gb

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
                       mock.Mock(return_value=['builder-0', 'builder-1']))
    @mock.patch.object(build.asyncio, 'sleep', mock.MagicMock)
    @gen_test
    def test_get_builders_polling(self):

        sleep_mock = mock.Mock()

        @asyncio.coroutine
        def sleep(n):
            sleep_mock()

        build.asyncio.sleep = sleep
        yield from self._create_test_data()
        self.manager.repository = self.repo

        self.manager.repository.poller.is_polling = mock.Mock(
            side_effect=[True, False])

        self.manager.repository.poller.vcs.checkout = mock.MagicMock()

        builders = yield from self.manager.get_builders(self.slave,
                                                        self.revision)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 2)
        self.assertTrue(sleep_mock.called)

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
    def test_execute_build_without_build(self):
        yield from self._create_test_data()

        self.manager._execute_in_parallel = mock.MagicMock()
        self.manager._build_queues[self.slave.name].extend(
            [self.buildset])
        slave = mock.Mock()
        slave.name = self.slave.name
        yield from self.manager._execute_builds(slave)
        self.assertFalse(self.manager._execute_in_parallel.called)

    @gen_test
    def test_execute_build(self):
        yield from self._create_test_data()

        self.manager._execute_in_parallel = mock.MagicMock()
        self.manager._build_queues[self.slave.name].extend(
            [self.buildset])
        yield from self.manager._execute_builds(self.slave)
        self.assertTrue(self.manager._execute_in_parallel.called)

    @gen_test
    def test_execute_in_parallel(self):
        yield from self._create_test_data()

        builds = [self.build, self.consumed_build]

        self.slave.build = asyncio.coroutine(lambda x: None)

        fs = yield from self.manager._execute_in_parallel(self.slave, builds)

        for f in fs:
            self.assertTrue(f.done())

    @gen_test
    def test_add_builds_from_signal(self):
        # ensures that builds are added when revision_added signal is sent.

        yield from self._create_test_data()
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
        self.buildset = build.BuildSet(repository=self.repo,
                                       revision=self.revision,
                                       commit='sdasf',
                                       commit_date=now)
        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder)
        self.buildset.builds.append(self.build)
        self.consumed_build = build.Build(repository=self.repo,
                                          slave=self.slave, branch='master',
                                          named_tree='v0.1',
                                          builder=self.builder,
                                          status='running')
        self.buildset.builds.append(self.consumed_build)

        yield self.buildset.save()


class BuilderTest(AsyncTestCase):

    @gen_test
    def tearDown(self):
        yield build.Builder.drop_collection()
        yield repository.Repository.drop_collection()
        yield build.BuildSet.drop_collection()
        yield repository.Slave.drop_collection()

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
                                builder=builder,
                                status='success', started=now())
        rev = repository.RepositoryRevision(commit='saçfijf',
                                            commit_date=now(),
                                            repository=repo,
                                            branch='master')
        yield rev.save()
        buildset = build.BuildSet(repository=repo, revision=rev,
                                  commit='asdasf', commit_date=now)
        buildset.builds.append(buildinst)
        yield buildset.save()
        status = yield from builder.get_status()

        self.assertEqual(status, 'success')

    @gen_test
    def test_to_dict(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234)
        yield slave_inst.save()
        builder = yield from build.Builder.create(repository=repo, name='b1')
        objdict = yield from builder.to_dict()
        self.assertEqual(objdict['id'], builder.id)
        self.assertTrue(objdict['status'])

    @gen_test
    def test_to_json(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        yield repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234)
        yield slave_inst.save()
        builder = yield from build.Builder.create(repository=repo, name='b1')
        objdict = build.json.loads((yield from builder.to_json()))
        self.assertTrue(isinstance(objdict['id'], str))
