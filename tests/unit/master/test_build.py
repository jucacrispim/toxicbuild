# -*- coding: utf-8 -*-

# Copyright 2015-2019 Juca Crispim <juca@poraodojuca.net>

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
from collections import defaultdict, deque
import datetime
from unittest import TestCase, mock
from toxicbuild.core.utils import now
from toxicbuild.master import build, repository, slave, users
from tests import async_test, AsyncMagicMock


class BuildStepTest(TestCase):

    def test_to_dict(self):
        bs = build.BuildStep(name='bla', command='ls', status='fail',
                             started=now(), finished=now(),
                             index=1)

        objdict = bs.to_dict()
        self.assertTrue(objdict['started'])
        self.assertIsNotNone(objdict.get('index'))

    def test_to_dict_total_time(self):
        bs = build.BuildStep(
            name='bla', command='ls', status='fail', started=now(),
            finished=now() + datetime.timedelta(seconds=2), total_time=2)

        objdict = bs.to_dict()
        self.assertEqual(objdict['total_time'], '0:00:02')

    def test_to_dict_no_output(self):
        bs = build.BuildStep(
            name='bla', command='ls', status='fail', started=now(),
            finished=now() + datetime.timedelta(seconds=2), total_time=2)

        objdict = bs.to_dict(output=False)
        self.assertNotIn('output', list(objdict.keys()))

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
        await users.User.drop_collection()

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
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

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
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
        self.assertTrue(bd['status'])
        self.assertTrue(bd['output'])

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict_external(self):
        await self._create_test_data()
        bs = build.BuildStep(name='bla',
                             command='ls',
                             started=now(),
                             finished=now(),
                             total_time=1,
                             status='finished')
        external = build.ExternalRevisionIinfo(
            url='http://somewhere.com/bla.git',
            name='somerepo', branch='master',
            into='into')
        self.buildset.builds[0].external = external
        self.buildset.builds[0].steps.append(bs)
        self.buildset.builds[0].total_time = 1
        bd = self.buildset.builds[0].to_dict()
        self.assertEqual(bd['total_time'], '0:00:01')
        self.assertTrue(bd.get('external'))

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict_builder_name(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        build._data['builder'] = self.builder
        d = build.to_dict()
        self.assertTrue(d['builder']['name'])

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict_no_builder_name(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        build_inst = await type(build_inst).get(build_inst.uuid)
        d = build_inst.to_dict()
        self.assertIsNone(d['builder'].get('name'))

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_update(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        b.status = 'fail'
        await b.update()

        buildset = await build.BuildSet.objects.get(id=self.buildset.id)
        self.assertEqual(buildset.builds[0].status, 'fail')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_update_without_save(self):
        await self._create_test_data()

        b = build.Build(branch='master', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1', number=0)

        with self.assertRaises(build.DBError):
            await b.update()

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_buildset(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        buildset = await b.get_buildset()
        self.assertEqual(buildset, self.buildset)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_output(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        expected = 'some command\nsome output\n\n'
        self.assertEqual(expected, build.output)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        r = await build.Build.get(b.uuid)
        self.buildset.builds[0]
        self.assertEqual(b, r)

    @async_test
    async def test_get_no_build(self):
        with self.assertRaises(build.Build.DoesNotExist):
            await build.Build.get(build.uuid4())

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @async_test
    async def test_notify(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        await build_inst.notify('build-added')
        self.assertTrue(build.build_notifications.publish.called)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @async_test
    async def test_cancel(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        slave = await build_inst.slave
        slave.queue_count += 1
        await slave.save()
        await build_inst.cancel()
        self.assertEqual(build_inst.status, 'cancelled')
        await slave.reload()
        self.assertEqual(slave.queue_count, 0)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @async_test
    async def test_cancel_no_slave(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        build_inst.slave = None
        await build_inst.update()
        await build_inst.cancel()
        self.assertEqual(build_inst.status, 'cancelled')

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_cancel_impossible(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        build_inst.status = 'running'
        with self.assertRaises(build.ImpossibleCancellation):
            await build_inst.cancel()

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_set_slave(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        await build.set_slave(self.slave)

        self.assertTrue(self.slave.queue_count)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_is_ready2run_no_trigger(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        r = await build.is_ready2run()

        self.assertTrue(r)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_is_ready2run_not_pending(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        build.status = 'cancelled'
        await build.update()
        r = await build.is_ready2run()

        self.assertFalse(r)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_is_ready2run_false(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        b.triggered_by = [
            build.BuildTrigger(
                **{'builder_name': 'br0',
                   'statuses': ['success']}),
        ]
        await b.update()

        br0 = build.Builder(repository=self.repo, name='br0')
        await br0.save()
        br1 = build.Builder(repository=self.repo, name='br1')
        await br1.save()

        b0 = build.Build(branch='master', builder=br0,
                         repository=self.repo, named_tree='v0.1', number=1)
        self.buildset.builds.append(b0)

        b1 = build.Build(branch='master', builder=br1,
                         repository=self.repo, named_tree='v0.1', number=2)
        self.buildset.builds.append(b1)

        await self.buildset.save()
        r = await b.is_ready2run()

        self.assertFalse(r)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_is_ready2run_none(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        b.triggered_by = [
            build.BuildTrigger(
                **{'builder_name': 'br0',
                   'statuses': ['success']}),
        ]
        await b.update()

        br0 = build.Builder(repository=self.repo, name='br0')
        await br0.save()
        br1 = build.Builder(repository=self.repo, name='br1')
        await br1.save()

        b0 = build.Build(branch='master', builder=br0, status='fail',
                         repository=self.repo, named_tree='v0.1', number=1)
        self.buildset.builds.append(b0)

        b1 = build.Build(branch='master', builder=br1,
                         repository=self.repo, named_tree='v0.1', number=2)
        self.buildset.builds.append(b1)

        await self.buildset.save()
        r = await b.is_ready2run()

        self.assertIsNone(r)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_is_ready2run_true(self):
        await self._create_test_data()
        b = self.buildset.builds[0]
        b.triggered_by = [
            build.BuildTrigger(
                **{'builder_name': 'br0',
                   'statuses': ['success']}),
        ]
        await b.update()

        br0 = build.Builder(repository=self.repo, name='br0')
        await br0.save()
        br1 = build.Builder(repository=self.repo, name='br1')
        await br1.save()

        b0 = build.Build(branch='master', builder=br0, status='success',
                         repository=self.repo, named_tree='v0.1', number=1)
        self.buildset.builds.append(b0)

        b1 = build.Build(branch='master', builder=br1,
                         repository=self.repo, named_tree='v0.1', number=2)
        self.buildset.builds.append(b1)

        await self.buildset.save()
        r = await b.is_ready2run()

        self.assertTrue(r)

    async def _create_test_data(self):
        self.owner = users.User(email='a@a.com', password='asfd')
        await self.owner.save()
        self.repo = repository.Repository(name='bla', url='git@bla.com',
                                          owner=self.owner)
        await self.repo.save()
        self.slave = slave.Slave(name='sla', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await self.slave.save()
        self.builder = build.Builder(repository=self.repo, name='builder-bla')
        await self.builder.save()
        b = build.Build(branch='master', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1', number=1)
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
        await build.BuildSet.drop_collection()
        await slave.Slave.drop_collection()
        await repository.Repository.drop_collection()
        await users.User.drop_collection()

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock())
    @async_test
    async def test_notify(self):
        await self._create_test_data()
        await self.buildset.notify('buildset-added')
        self.assertTrue(build.build_notifications.publish.called)

    @async_test
    async def test_get_buildset_number(self):
        await self._create_test_data()
        b = build.BuildSet(repository=self.repo,
                           revision=self.rev,
                           commit='alsdfjçasdfj',
                           commit_date=now(),
                           branch=self.rev.branch,
                           author=self.rev.author,
                           title=self.rev.title,
                           number=2,
                           builds=[self.build])
        await b.save()
        n = await build.BuildSet._get_next_number(self.repo)
        self.assertEqual(n, 3)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_create(self):
        await self._create_test_data()
        buildset = await build.BuildSet.create(self.repo, self.rev)
        self.assertTrue(buildset.commit)
        self.assertTrue(buildset.id)
        self.assertTrue(buildset.author)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict(self):
        await self._create_test_data()
        objdict = self.buildset.to_dict()
        self.assertEqual(len(objdict['builds']), 1)
        self.assertTrue(objdict['commit_date'])
        self.assertIn('commit_body', objdict)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict_no_builds(self):
        await self._create_test_data()
        objdict = self.buildset.to_dict(builds=False)
        self.assertEqual(len(objdict['builds']), 0)
        self.assertTrue(objdict['commit_date'])

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict_total_time(self):
        await self._create_test_data()
        self.buildset.total_time = 1
        objdict = self.buildset.to_dict()
        self.assertEqual(objdict['total_time'], '0:00:01')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_json(self):
        await self._create_test_data()

        objdict = build.json.loads(self.buildset.to_json())
        self.assertTrue(objdict['id'])

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_running(self):
        buildset = build.BuildSet()
        buildset.reload = AsyncMagicMock()
        buildset.save = AsyncMagicMock(spec=buildset.save)
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']
        for i in range(5):
            build_inst = build.Build(status=statuses[i], number=i)
            buildset.builds.append(build_inst)

        await buildset.update_status()
        status = buildset.status
        self.assertEqual(status, 'running')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_exception(self):
        buildset = build.BuildSet()
        buildset.reload = AsyncMagicMock()
        buildset.save = AsyncMagicMock(spec=buildset.save)
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']

        for i in range(5):
            if i > 0:
                build_inst = build.Build(status=statuses[i], number=i)
                buildset.builds.append(build_inst)

        await buildset.update_status()
        status = buildset.status
        self.assertEqual(status, 'exception')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_fail(self):
        buildset = build.BuildSet()
        buildset.save = AsyncMagicMock(spec=buildset.save)
        buildset.reload = AsyncMagicMock()

        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']
        for i in range(5):
            if i > 1:
                build_inst = build.Build(status=statuses[i], number=i)
                buildset.builds.append(build_inst)

        await buildset.update_status()
        status = buildset.status
        self.assertEqual(status, 'fail')

    @async_test
    async def test_get_status_no_builds(self):
        buildset = build.BuildSet()
        buildset.save = AsyncMagicMock(spec=buildset.save)
        buildset.reload = AsyncMagicMock()
        await buildset.update_status()
        status = buildset.status
        self.assertEqual(status, 'no builds')

    def test_get_pending_builds(self):
        buildset = build.BuildSet()
        statuses = ['running', 'exception', 'fail',
                    'warning', 'success', 'pending']

        for i in range(6):
            build_inst = build.Build(status=statuses[i], number=i)
            buildset.builds.append(build_inst)

        pending = buildset.get_pending_builds()
        self.assertEqual(len(pending), 1)

    @async_test
    async def test_aggregate_get(self):
        await self._create_test_data()
        self.buildset.commit_body = 'body'
        await self.buildset.save()
        buildset = await build.BuildSet.aggregate_get(id=self.buildset.id)
        self.assertTrue(buildset.id)
        self.assertTrue(buildset.builds)
        build_inst = buildset.builds[0]
        self.assertTrue(build_inst._data.get('builder').name)
        self.assertTrue(buildset.commit_body)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_builds_for_branch(self):
        await self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1', number=1)
        self.buildset.builds.append(b)
        builds = await self.buildset.get_builds_for(branch='other')
        self.assertEqual(len(builds), 1)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_builds_for_builder(self):
        await self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1', number=0)
        self.buildset.builds.append(b)
        b = build.Build(branch='other', builder=self.other_builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1', number=1)
        self.buildset.builds.append(b)

        builds = await self.buildset.get_builds_for(builder=self.builder)
        self.assertEqual(len(builds), 2)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_builds_for_builder_and_branch(self):
        await self._create_test_data()
        b = build.Build(branch='other', builder=self.builder,
                        repository=self.repo, slave=self.slave,
                        named_tree='v0.1', number=0)
        self.buildset.builds.append(b)

        builds = await self.buildset.get_builds_for(builder=self.builder,
                                                    branch='master')
        self.assertEqual(len(builds), 1)

    async def _create_test_data(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()
        self.repo = repository.Repository(name='bla', url='git@bla.com',
                                          owner=self.owner)
        await self.repo.save()
        self.slave = slave.Slave(name='sla', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await self.slave.save()
        self.builder = build.Builder(repository=self.repo, name='builder-bla')
        self.other_builder = build.Builder(
            repository=self.repo, name='builder-ble')
        await self.builder.save()
        self.build = build.Build(branch='master', builder=self.builder,
                                 repository=self.repo, slave=self.slave,
                                 named_tree='v0.1', number=0)
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
                                       number=1,
                                       builds=[self.build])
        await self.buildset.save()


@mock.patch.object(repository.Repository, 'schedule', mock.Mock())
class BuildExecuterTest(TestCase):

    def setUp(self):
        slv = slave.Slave()
        repo = repository.Repository()
        builds = [build.Build(slave=slv), build.Build(slave=slv)]
        self.executer = build.BuildExecuter(repo, builds)

    @mock.patch.object(repository.Repository, 'add_running_build', mock.Mock())
    @mock.patch.object(slave.Slave, 'build',
                       AsyncMagicMock(spec=slave.Slave.build))
    @mock.patch.object(repository.Repository, 'remove_running_build',
                       mock.Mock())
    @async_test
    async def test_run_build(self):
        build = self.executer.builds[0]
        self.executer._execute_builds = AsyncMagicMock()
        await self.executer._run_build(build)

        self.assertTrue(
            type(self.executer.repository).add_running_build.called)
        self.assertTrue(
            type(self.executer.repository).remove_running_build.called)
        self.assertEqual(len(self.executer._queue), 1)
        self.assertTrue(self.executer._execute_builds.called)

    @mock.patch.object(build.Build, 'is_ready2run', AsyncMagicMock(
        return_value=False))
    @mock.patch.object(build.BuildExecuter, '_run_build',
                       AsyncMagicMock(spec=build.BuildExecuter._run_build))
    @mock.patch.object(build.Build, 'cancel',
                       AsyncMagicMock(spec=build.Build.cancel))
    @mock.patch.object(build.BuildExecuter, '_handle_queue_changes',
                       AsyncMagicMock(
                           spec=build.BuildExecuter._handle_queue_changes))
    @async_test
    async def test_execute_builds_not_ready(self):
        await self.executer._execute_builds()

        self.assertFalse(self.executer._run_build.called)
        self.assertEqual(len(self.executer._queue), 2)

    @mock.patch.object(build.Build, 'is_ready2run', AsyncMagicMock(
        return_value=True))
    @mock.patch.object(build.BuildExecuter, '_run_build',
                       AsyncMagicMock(spec=build.BuildExecuter._run_build))
    @mock.patch.object(build.Build, 'cancel',
                       AsyncMagicMock(spec=build.Build.cancel))
    @mock.patch.object(build.BuildExecuter, '_handle_queue_changes',
                       AsyncMagicMock(
                           spec=build.BuildExecuter._handle_queue_changes))
    @async_test
    async def test_execute_builds_repo_paralell_builds_limit(self):
        self.executer.repository.parallel_builds = 1
        self.executer._running = 1
        await self.executer._execute_builds()

        self.assertFalse(self.executer._run_build.called)
        self.assertEqual(len(self.executer._queue), 2)

    @mock.patch.object(build.Build, 'is_ready2run', AsyncMagicMock(
        return_value=None))
    @mock.patch.object(build.BuildExecuter, '_run_build',
                       AsyncMagicMock(spec=build.BuildExecuter._run_build))
    @mock.patch.object(build.Build, 'cancel',
                       AsyncMagicMock(spec=build.Build.cancel))
    @mock.patch.object(build.BuildExecuter, '_handle_queue_changes',
                       AsyncMagicMock(
                           spec=build.BuildExecuter._handle_queue_changes))
    @async_test
    async def test_execute_builds_cancel_build(self):
        await self.executer._execute_builds()

        self.assertFalse(self.executer._run_build.called)
        self.assertEqual(len(self.executer._queue), 0)

    @mock.patch.object(build.Build, 'is_ready2run', AsyncMagicMock(
        return_value=True))
    @mock.patch.object(build.BuildExecuter, '_run_build',
                       AsyncMagicMock(spec=build.BuildExecuter._run_build))
    @mock.patch.object(build.Build, 'cancel',
                       AsyncMagicMock(spec=build.Build.cancel))
    @mock.patch.object(build.BuildExecuter, '_handle_queue_changes',
                       AsyncMagicMock(
                           spec=build.BuildExecuter._handle_queue_changes))
    @async_test
    async def test_execute_builds_run(self):
        await self.executer._execute_builds()

        self.assertTrue(self.executer._run_build.called)

    @mock.patch.object(build.asyncio, 'sleep', AsyncMagicMock())
    @mock.patch.object(
        build.BuildExecuter, '_execute_builds',
        AsyncMagicMock(spec=build.BuildExecuter._execute_builds))
    @async_test
    async def test_execute(self):

        async def sleep(t):
            self.executer._queue.pop(0)

        build.asyncio.sleep = sleep

        r = await self.executer.execute()

        self.assertTrue(build.BuildExecuter._execute_builds.called)
        self.assertTrue(r)
        self.assertFalse(self.executer._queue)

    @mock.patch.object(build.Build, 'get_buildset',
                       AsyncMagicMock(spec=build.Build.get_buildset))
    @async_test
    async def test_handle_queue_changes(self):
        buildset = mock.Mock()
        buildset.builds = self.executer.builds
        build.Build.get_buildset.return_value = buildset
        self.executer.builds[0].status = 'fail'

        await self.executer._handle_queue_changes()

        self.assertEqual(len(self.executer._queue), 1)


@mock.patch.object(repository.Repository, 'schedule', mock.Mock())
@mock.patch.object(repository.Repository, '_notify_repo_creation',
                   AsyncMagicMock())
class BuildManagerTest(TestCase):

    def setUp(self):
        super().setUp()

        repo = mock.MagicMock()
        repo.__self__ = repo
        repo.__func__ = lambda: None
        self.manager = build.BuildManager(repo)

    @mock.patch('aioamqp.protocol.logger', mock.Mock())
    @async_test
    async def tearDown(self):

        await slave.Slave.drop_collection()
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await repository.RepositoryRevision.drop_collection()
        await repository.Repository.drop_collection()
        await repository.Slave.drop_collection()
        build.BuildManager._build_queues = defaultdict(deque)
        build.BuildManager._is_building = defaultdict(lambda: False)
        super().tearDown()

    def test_class_attributes(self):
        # the build queues must be class attributes or builds will not
        # respect the queue
        self.assertTrue(hasattr(build.BuildManager, '_build_queues'))
        self.assertTrue(hasattr(build.BuildManager, '_is_building'))

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_get_highest_build_number(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        highest = await self.manager._get_highest_build_number()
        self.assertEqual(highest, 1)

    @async_test
    async def test_get_highest_build_number_no_buildset(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()
        self.repo = await repository.Repository.create(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', owner=self.owner)

        self.manager.repository = self.repo
        highest = await self.manager._get_highest_build_number()
        self.assertEqual(highest, 0)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build.buildset_added, 'send', mock.Mock(
        spec=build.buildset_added.send))
    @async_test
    async def test_add_builds_for_buildset(self):
        await self._create_test_data()
        b = build.Builder()
        b.repository = self.repo
        b.name = 'blabla'
        await b.save()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)
        self.manager.get_builders = AsyncMagicMock(
            return_value=([b, self.builder], 'master'))
        conf = {'builders': []}
        await self.manager.add_builds_for_buildset(self.buildset, conf)
        self.assertEqual(len(self.manager.build_queues), 1)
        buildset = self.manager.build_queues[0]
        # It already has two builds from _create_test_data and more two
        # from .add_builds_for_slave
        self.assertEqual(len(buildset.builds), 4)
        self.assertTrue(build.buildset_added.send.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_add_builds(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        self.manager.repository.get_config_for = AsyncMagicMock(
            spec=self.manager.repository.get_config_for)
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        self.manager.get_builders = AsyncMagicMock(
            spec=self.manager.get_builders,
            return_value=([self.builder], self.revision.branch))

        await self.manager.add_builds([self.revision])

        self.assertEqual(len(self.manager.build_queues), 1)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_add_builds_revision_dont_create(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        self.manager._execute_builds = asyncio.coroutine(lambda *a, **kw: None)

        @asyncio.coroutine
        def gb(branch, slave):
            return [self.builder]

        self.manager.get_builders = gb
        self.revision.body = 'some commit \n# ci: skip'
        await self.manager.add_builds([self.revision])

        self.assertEqual(len(self.manager.build_queues), 0)

    @async_test
    async def test_add_builds_no_last_bs(self):
        self.manager.cancel_previous_pending = AsyncMagicMock(
            spec=self.manager.cancel_previous_pending)
        await self.manager.add_builds([])
        self.assertFalse(self.manager.cancel_previous_pending.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_add_builds_not_only_latest(self):
        await self._create_test_data()
        self.manager._execute_builds = AsyncMagicMock(
            spec=self.manager._execute_builds)
        self.manager.get_builders = AsyncMagicMock(
            spec=self.manager.get_builders,
            return_value=[self.builder, self.revision.branch])
        self.manager.cancel_previous_pending = AsyncMagicMock(
            spec=self.manager.cancel_previous_pending)
        self.manager.repository = self.repo
        self.repo.branches = [repository.RepositoryBranch(
            name='master', notify_only_latest=False)]
        await self.manager.add_builds([self.revision])
        self.assertFalse(self.manager.cancel_previous_pending.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(return_value=[{'name': 'builder-0'},
                                               {'name': 'builder-1'}]))
    @async_test
    async def test_get_builders(self):
        await self._create_test_data()
        checkout = mock.MagicMock()
        self.repo.schedule = mock.Mock()
        await self.repo.bootstrap()
        self.manager.repository = self.repo
        self.manager.config_type = 'py'
        self.manager.repository.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())
        conf = mock.Mock()
        builders, origin = await self.manager.get_builders(self.revision,
                                                           conf)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 2)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(side_effect=[[], [{'name': 'builder-0'},
                                                   {'name': 'builder-1'}]]))
    @async_test
    async def test_get_builders_fallback(self):
        await self._create_test_data()
        checkout = mock.MagicMock()
        self.revision.branch = 'no-builders'
        self.revision.builders_fallback = 'master'
        self.repo.schedule = mock.Mock()
        await self.repo.bootstrap()
        self.manager.repository = self.repo
        self.manager.config_type = 'py'
        conf = mock.Mock()
        self.manager.repository.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())
        builders, origin = await self.manager.get_builders(self.revision,
                                                           conf)

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(origin, 'master')
        self.assertEqual(len(builders), 2)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(side_effect=AttributeError))
    @async_test
    async def test_get_builders_with_bad_toxicbuildconf(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        self.repo.schedule = mock.Mock()
        self.manager.log = mock.Mock()
        await self.repo.bootstrap()
        checkout = mock.MagicMock()
        conf = mock.Mock()
        self.manager.repository.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())
        builders, origin = await self.manager.get_builders(self.revision,
                                                           conf)

        self.assertFalse(builders)
        self.assertTrue(self.manager.log.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(return_value=[{'name': 'builder-0'},
                                               {'name': 'builder-1'}]))
    @async_test
    async def test_get_builders_include(self):
        await self._create_test_data()
        checkout = mock.MagicMock()
        self.repo.schedule = mock.Mock()
        await self.repo.bootstrap()
        self.manager.repository = self.repo
        self.manager.config_type = 'py'
        self.manager.repository.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())
        conf = mock.Mock()
        builders, origin = await self.manager.get_builders(self.revision,
                                                           conf,
                                                           include='builder-0')

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 1)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'list_builders_from_config',
                       mock.Mock(return_value=[{'name': 'builder-0'},
                                               {'name': 'builder-1'}]))
    @async_test
    async def test_get_builders_exclude(self):
        await self._create_test_data()
        checkout = mock.MagicMock()
        self.repo.schedule = mock.Mock()
        await self.repo.bootstrap()
        self.manager.repository = self.repo
        self.manager.config_type = 'py'
        self.manager.repository.vcs.checkout = asyncio.coroutine(
            lambda *a, **kw: checkout())
        conf = mock.Mock()
        builders, origin = await self.manager.get_builders(self.revision,
                                                           conf,
                                                           exclude='builder-0')

        for b in builders:
            self.assertTrue(isinstance(b, build.Document))

        self.assertEqual(len(builders), 1)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_execute_build_no_slaves(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        self.repo.slaves = []
        await self.repo.save()

        r = await self.manager._execute_builds()

        self.assertFalse(r)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_execute_build_without_build(self):
        await self._create_test_data()
        self.manager.repository = self.repo
        self.manager._execute_in_parallel = mock.MagicMock()
        self.buildset.builds[0].status = 'cancelled'
        await self.buildset.save()
        self.manager.build_queues.extend(
            [self.buildset])
        slave = mock.Mock()
        slave.name = self.slave.name
        slave.stop_instance = AsyncMagicMock()
        self.manager.repository = self.repo

        await self.manager._execute_builds()
        self.assertFalse(self.manager._execute_in_parallel.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build.BuildSet, 'reload', AsyncMagicMock())
    @mock.patch.object(build.BuildExecuter, 'execute',
                       AsyncMagicMock(spec=build.BuildExecuter.execute))
    @async_test
    async def test_execute_build(self):
        await self._create_test_data()

        self.manager.repository = self.repo
        self.manager.build_queues.extend([self.buildset])

        r = await self.manager._execute_builds()
        self.assertTrue(build.BuildExecuter.execute.called)
        self.assertTrue(r)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_set_started_for_buildset(self):
        await self._create_test_data()
        buildset = mock.MagicMock()
        save_mock = mock.MagicMock()
        buildset.save = asyncio.coroutine(lambda *a, **kw: save_mock())
        buildset.started = None
        buildset.notify = AsyncMagicMock()
        await self.manager._set_started_for_buildset(buildset)
        self.assertTrue(buildset.started)
        self.assertTrue(save_mock.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
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

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build.BuildSet, 'reload', AsyncMagicMock())
    @async_test
    async def test_set_finished_for_buildset(self):
        await self._create_test_data()
        self.buildset.started = now()
        await self.buildset.save()
        await self.manager._set_finished_for_buildset(self.buildset)
        bs = await type(self.buildset).objects.get(id=self.buildset.id)
        self.assertTrue(bs.finished)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build.BuildSet.objects, 'get', AsyncMagicMock())
    @async_test
    async def test_set_finished_for_buildset_already_finished(self):
        await self._create_test_data()
        started = now()
        finished = started + datetime.timedelta(days=20)
        self.buildset.finished = finished
        self.buildset.started = started
        await self.buildset.save()
        await self.manager._set_finished_for_buildset(self.buildset)
        self.assertTrue(self.buildset.finished is finished)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'now', mock.Mock())
    @mock.patch.object(build.BuildSet, 'reload', AsyncMagicMock())
    @async_test
    async def test_set_finished_for_buildset_total_time(self):
        just_now = now()
        build.now.return_value = just_now + datetime.timedelta(seconds=10)
        await self._create_test_data()
        self.buildset.started = build.localtime2utc(just_now)
        await self.buildset.save()
        await self.manager._set_finished_for_buildset(self.buildset)
        bs = await type(self.buildset).objects.get(id=self.buildset.id)
        self.assertEqual(bs.total_time, 10)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @async_test
    async def test_start_pending(self):
        await self._create_test_data()

        _eb_mock = mock.Mock()

        @asyncio.coroutine
        def _eb():
            _eb_mock()

        self.repo.build_manager._execute_builds = _eb
        await self.repo.build_manager.start_pending()
        await self.other_repo.build_manager.start_pending()
        self.assertEqual(_eb_mock.call_count, 1)

    @mock.patch.object(build.BuildSet, 'notify', mock.MagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'ensure_future', mock.Mock)
    @async_test
    async def test_start_pending_with_queue(self):
        await self._create_test_data()

        _eb_mock = mock.Mock()

        @asyncio.coroutine
        def _eb():
            _eb_mock()

        self.repo.build_manager._execute_builds = _eb
        self.repo.build_manager._build_queues = defaultdict(deque)
        self.repo.build_manager.build_queues.append(mock.Mock())
        build.ensure_future = mock.Mock()
        await self.repo.build_manager.start_pending()
        self.assertFalse(build.ensure_future.called)

    @mock.patch.object(build.BuildSet, 'notify', mock.MagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(repository.repo_added, 'publish', AsyncMagicMock())
    @mock.patch.object(repository.scheduler_action, 'publish',
                       AsyncMagicMock())
    @mock.patch.object(build, 'ensure_future', mock.Mock)
    @async_test
    async def test_start_pending_with_working_slave(self):
        await self._create_test_data()

        _eb_mock = mock.Mock()

        @asyncio.coroutine
        def _eb():
            _eb_mock()

        self.repo.build_manager._execute_builds = _eb
        self.repo.build_manager._is_building[self.repo.id] = True
        build.ensure_future = mock.Mock()
        await self.repo.build_manager.start_pending()
        self.assertFalse(build.ensure_future.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(build.Build, 'notify', AsyncMagicMock(
        spec=build.Build.notify))
    @async_test
    async def test_cancel_build(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        await self.repo.build_manager.cancel_build(str(build.uuid))
        bs = await type(self.buildset).objects.get(id=self.buildset.id)
        self.assertEqual(bs.builds[0].status, 'cancelled')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(build.Build, 'notify', AsyncMagicMock(
        spec=build.Build.notify))
    @async_test
    async def test_cancel_build_impossible(self):
        await self._create_test_data()
        build = self.buildset.builds[0]
        build.status = 'running'
        await build.update()
        self.repo.build_manager.log = mock.Mock()
        await self.repo.build_manager.cancel_build(build.uuid)
        self.assertTrue(self.repo.build_manager.log.called)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @async_test
    async def test_notify(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        await build_inst.notify('build-added')
        self.assertTrue(build.build_notifications.publish.called)

    @mock.patch.object(build.build_notifications, 'publish', AsyncMagicMock(
        spec=build.build_notifications.publish))
    @async_test
    async def test_cancel_previous_pending(self):
        await self._create_test_data()
        bs = await build.BuildSet.create(repository=self.repo,
                                         revision=self.revision)
        await self.repo.build_manager.cancel_previous_pending(bs)
        old_bs = await build.BuildSet.objects.get(id=self.buildset.id)
        self.assertEqual(old_bs.builds[0].status, 'cancelled')
        self.assertEqual(old_bs.get_status(), 'running')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(build.Build, 'notify', AsyncMagicMock(
        spec=build.Build.notify))
    @async_test
    async def test_set_slave(self):
        await self._create_test_data()
        await self.repo.build_manager._set_slave(self.build)
        s = await self.build.slave
        self.assertTrue(s.id)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(build.Build, 'notify', AsyncMagicMock(
        spec=build.Build.notify))
    @async_test
    async def test_handle_build_triggered_by(self):
        await self._create_test_data()
        b = build.Build(triggered_by=[{'builder_name': 'builder-1'},
                                      {'builder_name': 'builder-2'}])
        builders = [build.Builder(name='builder-1')]
        self.repo.build_manager._handle_build_triggered_by(b, builders)

        self.assertEqual(len(b.triggered_by), 1)

    async def _create_test_data(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()
        self.slave = slave.Slave(host='127.0.0.1', port=7777, name='slave',
                                 token='123', owner=self.owner)
        self.slave.build = asyncio.coroutine(lambda x: None)
        await self.slave.save()

        self.repo = await repository.Repository.create(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave], owner=self.owner)

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
                                 builder=self.builder, number=0)
        self.buildset.builds.append(self.build)
        self.consumed_build = build.Build(repository=self.repo,
                                          slave=self.slave, branch='master',
                                          named_tree='v0.1',
                                          builder=self.builder,
                                          status='running', number=1)
        self.buildset.builds.append(self.consumed_build)

        await self.buildset.save()

        self.other_repo = repository.Repository(
            name='otherreponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave],
            owner=self.owner)

        await self.other_repo.save()


class BuilderTest(TestCase):

    @async_test
    async def tearDown(self):
        await build.Builder.drop_collection()
        await repository.Repository.drop_collection()
        await build.BuildSet.drop_collection()
        await repository.Slave.drop_collection()

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_create(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()

        builder = await build.Builder.create(repository=repo, name='b1')
        self.assertTrue(builder.id)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()

        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()
        builder = await build.Builder.create(repository=repo, name='b1')

        returned = await build.Builder.get(repository=repo, name='b1')

        self.assertEqual(returned, builder)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(build.Builder, 'create', mock.MagicMock())
    @async_test
    async def test_get_or_create_with_create(self):

        create = mock.MagicMock()
        build.Builder.create = asyncio.coroutine(lambda * a, **kw: create())
        await build.Builder.get_or_create(name='bla')

        self.assertTrue(create.called)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @mock.patch.object(build.Builder, 'create', mock.MagicMock())
    @async_test
    async def test_get_or_create_with_get(self):
        create = mock.MagicMock()
        build.Builder.create = asyncio.coroutine(lambda *a, **kw: create())
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()

        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()
        builder = await build.Builder.create(repository=repo, name='b1')

        returned = await build.Builder.get_or_create(
            repository=repo, name='b1')

        self.assertEqual(returned, builder)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_without_build(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()

        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        status = await builder.get_status()

        self.assertEqual(status, 'idle')

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()
        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await slave_inst.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        buildinst = build.Build(repository=repo, slave=slave_inst,
                                branch='master', named_tree='v0.1',
                                builder=builder,
                                status='success', started=now(), number=0)
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

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_dict(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()

        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await slave_inst.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        objdict = await builder.to_dict()
        self.assertEqual(objdict['id'], str(builder.id))
        self.assertTrue(objdict['status'])

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_to_json(self):
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()

        repo = repository.Repository(name='bla', url='git@bla.com',
                                     update_seconds=300, vcs_type='git',
                                     owner=self.owner)
        await repo.save()
        slave_inst = slave.Slave(name='bla', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await slave_inst.save()
        builder = await build.Builder.create(repository=repo, name='b1')
        objdict = build.json.loads((await builder.to_json()))
        self.assertTrue(isinstance(objdict['id'], str))
