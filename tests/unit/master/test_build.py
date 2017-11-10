# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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
from collections import defaultdict, deque
import datetime
from unittest import TestCase, mock
from toxicbuild.core.utils import now
from toxicbuild.master import build, repository, slave
from tests import async_test


class BuildStepTest(TestCase):

    def test_to_dict(self):
        bs = build.BuildStep(name='bla', command='ls', status='fail',
                             started=now(), finished=now())

        objdict = bs.to_dict()
        self.assertTrue(objdict['started'])

    def test_to_dict_total_time(self):
        bs = build.BuildStep(
            name='bla', command='ls', status='fail', started=now(),
            finished=now() + datetime.timedelta(seconds=2), total_time=2)

        objdict = bs.to_dict()
        self.assertEqual(objdict['total_time'], '0:00:02')

    def test_to_json(self):
        bs = build.BuildStep(name='bla',
                             command='ls',
                             status='pending')
        bsd = build.json.loads(bs.to_json())
        self.assertIn('finished', bsd.keys())


class BuildTest(TestCase):

    @async_test
    async def tearDown(self):
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await slave.Slave.drop_collection()
        await repository.RepositoryRevision.drop_collection()
        await repository.Repository.drop_collection()

    @async_test
    async def test_to_json(self):
        await self._create_test_data()
        bs = build.BuildStep(name='bla',
                             command='ls',
                             status='pending')
        self.buildset.builds[0].steps.append(bs)
        bd = build.json.loads(self.buildset.builds[0].to_json())
        self.assertIn('finished', bd['steps'][0].keys())
        self.assertTrue(bd['builder']['id'])

    @async_test
    async def test_to_dict(self):
        await self._create_test_data()
        bs = build.BuildStep(name='bla',
                             command='ls',
                             started=now(),
                             finished=now(),
                             total_time=1,
                             status='finished')
        self.buildset.builds[0].steps.append(bs)
        self.buildset.builds[0].total_time = 1
        bd = self.buildset.builds[0].to_dict()
        self.assertEqual(bd['total_time'], '0:00:01')

    @async_test
    async def test_update(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        b.status = 'fail'
        await b.update()

        buildset = await build.BuildSet.objects.get(id=self.buildset.id)
        self.assertEqual(buildset.builds[0].status, 'fail')

    @async_test
    async def test_update_without_save(self):
        await self._create_test_data()

        b = build.Build(branch='master', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')

        with self.assertRaises(build.DBError):
            await b.update()

    @async_test
    async def test_get_buildset(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        buildset = await b.get_buildset()
        self.assertEqual(buildset, self.buildset)

    @async_test
    async def test_get_output(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        expected = 'some command\nsome output'
        self.assertEqual(expected, build.output)

    async def _create_test_data(self):
        self.repo = repository.Repository(name='bla', url='git@bla.com')
        await self.repo.save()
        self.slave = slave.Slave(name='sla', host='localhost', port=1234,
                                 token='123')
        await self.slave.save()
        self.builder = build.Builder(repository=self.repo, name='builder-bla')
        await self.builder.save()
        b = build.Build(branch='master', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        s = build.BuildStep(name='some step', output='some output',
                            command='some command')
        b.steps.append(s)
        self.rev = repository.RepositoryRevision(commit='saçfijf',
                                                 commit_date=now(),
                                                 repository=self.repo,
                                                 branch='master',
                                                 author='tião',
                                                 title='blabla')
        await self.rev.save()

        self.buildset = await build.BuildSet.create(repository=self.repo,
                                                    revision=self.rev)
        self.buildset.builds.append(b)
        await self.buildset.save()


class BuildSetTest(TestCase):

    @async_test
    async def tearDown(self):
        await repository.Repository.drop_collection()
        await slave.Slave.drop_collection()
        await build.BuildSet.drop_collection()

    @async_test
    async def test_create(self):
        await self._create_test_data()
        buildset = await build.BuildSet.create(self.repo, self.rev)
        self.assertTrue(buildset.commit)
        self.assertTrue(buildset.id)
        self.assertTrue(buildset.author)

    @async_test
    async def test_create_without_save(self):
        await self._create_test_data()
        buildset = await build.BuildSet.create(self.repo, self.rev,
                                               save=False)
        self.assertFalse(buildset.id)

    @async_test
    async def test_to_dict(self):
        await self._create_test_data()
        objdict = self.buildset.to_dict()
        self.assertEqual(len(objdict['builds']), 1)
        self.assertTrue(objdict['commit_date'])

    @async_test
    async def test_to_dict_total_time(self):
        await self._create_test_data()
        self.buildset.total_time = 1
        objdict = self.buildset.to_dict()
        self.assertEqual(objdict['total_time'], '0:00:01')

    @async_test
    async def test_to_json(self):
        await self._create_test_data()

        objdict = build.json.loads(self.buildset.to_json())
        self.assertTrue(objdict['id'])

    @async_test
    async def test_status_running(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']
        for i in range(5):
            build_inst = build.Build(status=statuses[i])
            buildset.builds.append(build_inst)

        status = buildset.get_status()
        self.assertEqual(status, 'running')

    @async_test
    async def test_status_exception(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']

        for i in range(5):
            if i > 0:
                build_inst = build.Build(status=statuses[i])
                buildset.builds.append(build_inst)

        status = buildset.get_status()
        self.assertEqual(status, 'exception')

    @async_test
    async def test_status_fail(self):
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

    @async_test
    async def test_get_builds_for_branch(self):
        await self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)
        builds = await self.buildset.get_builds_for(branch='other')
        self.assertEqual(len(builds), 1)

    @async_test
    async def test_get_builds_for_builder(self):
        await self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)
        b = build.Build(branch='other', builder=self.other_builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)

        builds = await self.buildset.get_builds_for(builder=self.builder)
        self.assertEqual(len(builds), 2)

    @async_test
    async def test_get_builds_for_builder_and_branch(self):
        await self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1')
        self.buildset.builds.append(b)

        builds = await self.buildset.get_builds_for(builder=self.builder,
                                                    branch='master')
        self.assertEqual(len(builds), 1)

    async def _create_test_data(self):
        self.repo = repository.Repository(name='bla', url='git@bla.com')
        await self.repo.save()
        self.slave = slave.Slave(name='sla', host='localhost', port=1234,
                                 token='123')
        await self.slave.save()
        self.builder = build.Builder(repository=self.repo, name='builder-bla')
        self.other_builder = build.Builder(
            repository=self.repo, name='builder-ble')
        await self.builder.save()
        self.build = build.Build(branch='master', builder=self.builder,
                                 repository=self.repo, slave=self.slave,
                                 named_tree='v0.1')
        self.rev = repository.RepositoryRevision(commit='saçfijf',
                                                 commit_date=now(),
                                                 repository=self.repo,
                                                 branch='master',
                                                 author='ze',
                                                 title='fixes #3')
        await self.rev.save()
        self.buildset = build.BuildSet(repository=self.repo,
                                       revision=self.rev,
                                       commit='alsdfjçasdfj',
                                       commit_date=now(),
                                       branch=self.rev.branch,
                                       author=self.rev.author,
                                       title=self.rev.title,
                                       builds=[self.build])
        await self.buildset.save()


class BuildManagerTest(TestCase):

    def setUp(self):
        super().setUp()

        repo = mock.MagicMock()
        repo.__self__ = repo
        repo.__func__ = lambda: None
        self.manager = build.BuildManager(repo)

    @async_test
    async def tearDown(self):
        await slave.Slave.drop_collection()
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await repository.RepositoryRevision.drop_collection()
        await repository.Repository.drop_collection()
        await repository.Slave.drop_collection()
        build.BuildManager._build_queues = defaultdict(
            lambda: defaultdict(deque))
        build.BuildManager._is_building = defaultdict(
            lambda: defaultdict(lambda: False))
        super().tearDown()

    def test_class_attributes(self):
        # the build queues must be class attributes or builds will not
        # respect the queue
        self.assertTrue(hasattr(build.BuildManager, '_build_queues'))
        self.assertTrue(hasattr(build.BuildManager, '_is_building'))

    @async_test
    async def test_add_builds_for_slave(self):
        await self._create_test_data()
        b = build.Builder()
        b.repository = self.repo
        b.name = 'blabla'
        await b.save()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        await self.manager.add_builds_for_slave(self.buildset, self.slave,
                                                [b, self.builder])
        self.assertEqual(len(self.manager.build_queues[self.slave.name]), 1)
        buildset = self.manager.build_queues[self.slave.name][0]
        # It already has two builds from _create_test_data and more two
        # from .add_builds_for_slave
        self.assertEqual(len(buildset.builds), 4)

    @async_test
    async def test_add_builds(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        @asyncio.coroutine
        def gb(branch, slave):
            return [self.builder]

        self.manager.get_builders = gb

        await self.manager.add_builds([self.revision])

        self.assertEqual(len(self.manager.build_queues[self.slave.name]), 1)

    @mock.patch.object(build, 'get_toxicbuildconf', mock.Mock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(return_value=['builder-0', 'builder-1']))
    @async_test
    async def test_get_builders(self):
        await self._create_test_data()
        checkout = mock.MagicMock()
        self.manager.repository = self.repo
        self.manager.repository.poller.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())

        builders = await self.manager.get_builders(self.slave,
                                                   self.revision)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 2)

    @mock.patch.object(build, 'get_toxicbuildconf', mock.Mock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(return_value=['builder-0', 'builder-1']))
    @mock.patch.object(build.asyncio, 'sleep', mock.MagicMock)
    @async_test
    async def test_get_builders_polling(self):

        sleep_mock = mock.Mock()

        @asyncio.coroutine
        def sleep(n):
            sleep_mock()

        build.asyncio.sleep = sleep
        await self._create_test_data()
        self.manager.repository = self.repo

        self.manager.repository.poller.is_polling = mock.Mock(
            side_effect=[True, False])

        checkout = mock.MagicMock()
        self.manager.repository.poller.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())

        builders = await self.manager.get_builders(self.slave,
                                                   self.revision)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 2)
        self.assertTrue(sleep_mock.called)

    @mock.patch.object(build, 'get_toxicbuildconf', mock.Mock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(side_effect=AttributeError))
    @mock.patch.object(build, 'log', mock.Mock())
    @async_test
    async def test_get_builders_with_bad_toxicbuildconf(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        checkout = mock.MagicMock()
        self.manager.repository.poller.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())

        builders = await self.manager.get_builders(self.slave,
                                                   self.revision)
        self.assertFalse(builders)
        self.assertTrue(build.log.called)

    @async_test
    async def test_execute_build_without_build(self):
        await self._create_test_data()

        self.manager._execute_in_parallel = mock.MagicMock()
        self.manager.build_queues[self.slave.name].extend(
            [self.buildset])
        slave = mock.Mock()
        slave.name = self.slave.name
        await self.manager._execute_builds(slave)
        self.assertFalse(self.manager._execute_in_parallel.called)

    @async_test
    async def test_execute_build(self):
        await self._create_test_data()

        run_in_parallel = mock.MagicMock()
        self.manager._execute_in_parallel = asyncio.coroutine(
            lambda *a, **kw: run_in_parallel())
        self.manager.build_queues[self.slave.name].extend(
            [self.buildset])
        await self.manager._execute_builds(self.slave)
        self.assertTrue(run_in_parallel.called)

    @async_test
    async def test_execute_in_parallel(self):
        await self._create_test_data()

        builds = [self.build, self.consumed_build]

        self.slave.build = asyncio.coroutine(lambda x: None)

        fs = await self.manager._execute_in_parallel(self.slave, builds)

        for f in fs:
            self.assertTrue(f.done())

    @async_test
    async def test_get_builds_chunks_with_limitless_parallels(self):
        await self._create_test_data()
        self.manager.repository.parallel_builds = None
        chunks = list(self.manager._get_builds_chunks([mock.Mock(),
                                                       mock.Mock()]))
        self.assertEqual(len(chunks), 1)

    @async_test
    async def test_get_builds_chunks_with_limit(self):
        await self._create_test_data()
        self.manager.repository.parallel_builds = 1
        chunks = list(self.manager._get_builds_chunks([mock.Mock(),
                                                       mock.Mock()]))
        self.assertEqual(len(chunks), 2)

    @async_test
    async def test_set_started_for_buildset(self):
        await self._create_test_data()
        buildset = mock.MagicMock()
        save_mock = mock.MagicMock()
        buildset.save = asyncio.coroutine(lambda *a, **kw: save_mock())
        buildset.started = None
        await self.manager._set_started_for_buildset(buildset)
        self.assertTrue(buildset.started)
        self.assertTrue(save_mock.called)

    @async_test
    async def test_set_started_for_buildset_already_started(self):
        await self._create_test_data()
        buildset = mock.MagicMock()
        save_mock = mock.MagicMock()
        just_now = mock.MagicMock()
        buildset.save = asyncio.coroutine(lambda *a, **kw: save_mock())
        buildset.started = just_now
        await self.manager._set_started_for_buildset(buildset)
        self.assertTrue(buildset.started is just_now)
        self.assertFalse(save_mock.called)

    @async_test
    async def test_set_finished_for_buildset(self):
        await self._create_test_data()
        buildset = mock.MagicMock()
        save_mock = mock.MagicMock()
        buildset.save = asyncio.coroutine(lambda *a, **kw: save_mock())
        buildset.finished = None
        await self.manager._set_finished_for_buildset(buildset)
        self.assertTrue(buildset.finished)
        self.assertTrue(save_mock.called)

    @async_test
    async def test_set_finished_for_buildset_already_finished(self):
        await self._create_test_data()
        buildset = mock.MagicMock()
        save_mock = mock.MagicMock()
        buildset.save = asyncio.coroutine(lambda *a, **kw: save_mock())
        finished = now() + datetime.timedelta(days=20)
        buildset.finished = finished
        await self.manager._set_finished_for_buildset(buildset)
        self.assertTrue(buildset.finished is finished)
        self.assertFalse(save_mock.called)

    @mock.patch.object(build, 'now', mock.Mock())
    @async_test
    async def test_set_finished_for_buildset_total_time(self):
        await self._create_test_data()
        buildset = mock.MagicMock()
        save_mock = mock.MagicMock()
        buildset.save = asyncio.coroutine(lambda *a, **kw: save_mock())
        buildset.started = now()
        build.now.return_value = buildset.started + datetime.timedelta(
            seconds=10)
        buildset.finished = None
        await self.manager._set_finished_for_buildset(buildset)
        self.assertEqual(buildset.total_time, 10)
        self.assertTrue(save_mock.called)

    @async_test
    async def test_add_builds_from_signal(self):
        # ensures that builds are added when revision_added signal is sent.

        await self._create_test_data()
        add_builds = mock.MagicMock()
        self.repo.build_manager.add_builds = asyncio.coroutine(
            lambda *a, **kw: add_builds(*a, **kw))
        ret = self.repo.poller.notify_change(*[self.revision])
        futures = [r[1] for r in ret]
        await asyncio.gather(*futures)
        self.assertTrue(add_builds.called)

    @mock.patch.object(build, 'ensure_future', mock.Mock())
    @async_test
    async def test_start_pending(self):
        await self._create_test_data()

        _eb_mock = mock.Mock()

        @asyncio.coroutine
        def _eb(slave):
            _eb_mock()

        self.buildset == self.buildset
        self.repo.build_manager._execute_builds = _eb
        await self.repo.build_manager.start_pending()
        await self.other_repo.build_manager.start_pending()
        self.assertEqual(build.ensure_future.call_count, 1)

    @mock.patch.object(build, 'ensure_future', mock.Mock)
    @async_test
    async def test_start_pending_with_queue(self):
        await self._create_test_data()

        _eb_mock = mock.Mock()

        @asyncio.coroutine
        def _eb(slave):
            _eb_mock()

        self.repo.build_manager._execute_builds = _eb
        self.repo.build_manager._build_queues[self.repo.name][
            self.slave.name] = mock.Mock()
        build.ensure_future = mock.Mock()
        await self.repo.build_manager.start_pending()
        self.assertFalse(build.ensure_future.called)

    @mock.patch.object(build, 'ensure_future', mock.Mock)
    @async_test
    async def test_start_pending_with_working_slave(self):
        await self._create_test_data()

        _eb_mock = mock.Mock()

        @asyncio.coroutine
        def _eb(slave):
            _eb_mock()

        self.repo.build_manager._execute_builds = _eb
        self.repo.build_manager._is_building[self.repo.name][
            self.slave.name] = True
        build.ensure_future = mock.Mock()
        await self.repo.build_manager.start_pending()
        self.assertFalse(build.ensure_future.called)

    @async_test
    async def test_test_disconnect_from_signals(self):
        await self._create_test_data()
        self.repo.build_manager.disconnect_from_signals()
        self.assertFalse(self.repo.build_manager._is_connected_to_signals)

    async def _create_test_data(self):
        self.slave = slave.Slave(host='127.0.0.1', port=7777, name='slave',
                                 token='123')
        self.slave.build = asyncio.coroutine(lambda x: None)
        await self.slave.save()
        self.repo = repository.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        await self.repo.save()

        self.revision = repository.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now(),
            author='ze', title='fixes nothing'
        )

        await self.revision.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        await self.builder.save()
        self.buildset = await build.BuildSet.create(
            repository=self.repo, revision=self.revision)

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

        await self.buildset.save()

        self.other_repo = repository.Repository(
            name='otherreponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        await self.other_repo.save()


class BuilderTest(TestCase):

    @async_test
    async def tearDown(self):
        await build.Builder.drop_collection()
        await repository.Repository.drop_collection()
        await build.BuildSet.drop_collection()
        await repository.Slave.drop_collection()

    @async_test
    async def test_create(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()

        builder = await build.Builder.create(repository=repo, name='b1')
        self.assertTrue(builder.id)

    @async_test
    async def test_get(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()
        builder = await build.Builder.create(repository=repo, name='b1')

        returned = await build.Builder.get(repository=repo, name='b1')

        self.assertEqual(returned, builder)

    @mock.patch.object(build.Builder, 'create', mock.MagicMock())
    @async_test
    async def test_get_or_create_with_create(self):

        create = mock.MagicMock()
        build.Builder.create = asyncio.coroutine(lambda * a, **kw: create())
        await build.Builder.get_or_create(name='bla')

        self.assertTrue(create.called)

    @mock.patch.object(build.Builder, 'create', mock.MagicMock())
    @async_test
    async def test_get_or_create_with_get(self):
        create = mock.MagicMock()
        build.Builder.create = asyncio.coroutine(lambda *a, **kw: create())
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()
        builder = await build.Builder.create(repository=repo, name='b1')

        returned = await build.Builder.get_or_create(
            repository=repo, name='b1')

        self.assertEqual(returned, builder)

    @async_test
    async def test_get_status_without_build(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        status = await builder.get_status()

        self.assertEqual(status, 'idle')

    @async_test
    async def test_get_status(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234,
                                 token='123')
        await slave_inst.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        buildinst = build.Build(repository=repo, slave=slave_inst,
                                branch='master', named_tree='v0.1',
                                builder=builder,
                                status='success', started=now())
        rev = repository.RepositoryRevision(commit='saçfijf',
                                            commit_date=now(),
                                            repository=repo,
                                            branch='master',
                                            author='bla',
                                            title='some title')
        await rev.save()
        buildset = await build.BuildSet.create(repository=repo,
                                               revision=rev)

        buildset.builds.append(buildinst)
        await buildset.save()
        status = await builder.get_status()

        self.assertEqual(status, 'success')

    @async_test
    async def test_to_dict(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234,
                                 token='123')
        await slave_inst.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        objdict = await builder.to_dict()
        self.assertEqual(objdict['id'], builder.id)
        self.assertTrue(objdict['status'])

    @async_test
    async def test_to_json(self):
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git')
        await repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234,
                                 token='123')
        await slave_inst.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        objdict = build.json.loads((await builder.to_json()))
        self.assertTrue(isinstance(objdict['id'], str))
