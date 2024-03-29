# -*- coding: utf-8 -*-

# Copyright 2015-2020, 2023 Juca Crispim <juca@poraodojuca.net>

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

import datetime
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from asyncamqp.exceptions import ConsumerTimeout
from toxicbuild.core import utils
from toxicbuild.master import (repository, build, slave, users)

from tests import async_test
from .utils import RepoTestData


class RepositoryTest(TestCase, RepoTestData):

    @async_test
    async def setUp(self):
        super(RepositoryTest, self).setUp()
        await self._create_db_revisions()
        repository.Repository._running_builds = 0
        repository._update_code_hashes = {}

    @async_test
    async def tearDown(self):
        await repository.Repository.drop_collection()
        await repository.RepositoryRevision.drop_collection()
        await repository.BuildSet.drop_collection()
        await slave.Slave.drop_collection()
        await build.Builder.drop_collection()
        await users.User.drop_collection()
        super(RepositoryTest, self).tearDown()

    @async_test
    async def test_to_dict(self):
        d = await self.repo.to_dict()
        self.assertTrue(d['id'])
        self.assertIn('slaves', d)

    @async_test
    async def test_to_dict_short(self):
        d = await self.repo.to_dict(short=True)
        self.assertTrue(d['id'])
        self.assertNotIn('slaves', d)

    @patch.object(repository, 'notifications', AsyncMock(
        spec=repository.notifications))
    @async_test
    async def test_request_removal(self):
        await self.repo.request_removal()
        self.assertTrue(repository.notifications.publish.called)

    @async_test
    async def test_request_code_update(self):
        await self.repo.request_code_update()
        self.GOT_MSG = False
        async with await repository.notifications.consume(
                routing_key='update-code-requested', timeout=5000) as consumer:
            try:
                async for msg in consumer:
                    await msg.acknowledge()
                    self.GOT_MSG = True
                    break
            except ConsumerTimeout:
                pass
        self.assertTrue(self.GOT_MSG)

    @patch.object(repository, 'ui_notifications', AsyncMock())
    @patch.object(repository.Repository, 'log', Mock())
    @patch.object(repository.Repository, 'schedule', Mock(
        spec=repository.Repository.schedule))
    @async_test
    async def test_create(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123',
                                              owner=self.owner)
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst])

        self.assertTrue(repo.id)
        self.assertTrue(repository.ui_notifications.publish.called)
        slaves = await repo.slaves
        self.assertEqual(slaves[0], slave_inst)
        self.assertTrue(repository.Repository.schedule.called)

    @patch.object(repository, 'ui_notifications', AsyncMock())
    @patch.object(repository.Repository, 'log', Mock())
    @patch.object(repository.Repository, 'schedule', Mock(
        spec=repository.Repository.schedule))
    @async_test
    async def test_create_with_branches(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123;_',
                                              owner=self.owner)
        branches = [repository.RepositoryBranch(name='branch{}'.format(str(i)),
                                                notify_only_latest=bool(i))
                    for i in range(3)]

        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst],
            branches=branches)

        self.assertTrue(repo.id)
        self.assertTrue(repository.Repository.schedule.called)
        self.assertEqual(len(repo.branches), 3)

    @patch.object(repository, 'ui_notifications', AsyncMock())
    @patch.object(repository.Repository, 'log', Mock())
    @patch.object(repository.Repository, 'schedule', Mock(
        spec=repository.Repository.schedule))
    @async_test
    async def test_create_dont_schedule(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123',
                                              owner=self.owner)
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst],
            schedule_poller=False)

        self.assertTrue(repo.id)
        self.assertTrue(repository.ui_notifications.publish.called)
        slaves = await repo.slaves
        self.assertEqual(slaves[0], slave_inst)
        self.assertFalse(repository.Repository.schedule.called)

    @async_test
    async def test_save_change_name(self):
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git')
        repo.name = 'new-reponame'
        await repo.save()
        self.assertEqual(repo.full_name, 'zezinho/new-reponame')

    @async_test
    async def test_save_change_owner(self):
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git')
        new_owner = users.User(email='huguinho@nada.co', password='123')
        await new_owner.save()
        repo.owner = new_owner
        await repo.save()
        self.assertEqual(repo.full_name, 'huguinho/reponame')

    @patch.object(repository, 'ui_notifications', AsyncMock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_remove(self):
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git')

        repo.schedule()
        builder = repository.Builder(name='b1', repository=repo)
        await builder.save()
        await repo.remove()

        builders_count = await repository.Builder.objects.filter(
            repository=repo).count()

        self.assertEqual(builders_count, 0)

        with self.assertRaises(repository.Repository.DoesNotExist):
            await repository.Repository.get(url=repo.url)

        self.assertIsNone(repository._scheduler_hashes.get(repo.url))
        self.assertIsNone(repository._scheduler_hashes.get(
            '{}-start-pending'.format(repo.url)))
        self.assertTrue(repository.scheduler_action.publish.called)

    @patch.object(repository, 'ui_notifications', AsyncMock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_get(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123',
                                              owner=self.owner)
        old_repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst])

        new_repo = await repository.Repository.get(url=old_repo.url)

        slaves = await new_repo.slaves
        self.assertEqual(old_repo, new_repo)
        self.assertEqual(slaves[0], slave_inst)

    @patch.object(repository, 'get_poller_client', MagicMock())
    @patch.object(repository.BuildManager, 'add_builds', AsyncMock(
        spec=repository.BuildManager.add_builds))
    @patch.object(repository.ui_notifications, 'publish', AsyncMock(
        spec=repository.ui_notifications.publish))
    @async_test
    async def test_update_code(self):
        repository.get_poller_client.return_value.__aenter__.return_value = \
            AsyncMock(poll_repo=AsyncMock(
                return_value={
                    'revisions': [
                        {
                            'commit': 'adsf',
                            'branch': 'master',
                            'commit_date': '4 04 25 23:49:19 2019 +0000',
                            'author': 'me',
                            'title': 'zhe-commit'}],
                    'clone_status': 'success',
                    'with_clone': False}))
        repo = await type(self.repo).objects.get(id=self.repo.id)
        repo.url = 'https://new-url.com/bla'
        await repo.save()
        await self.repo.update_code()
        self.assertTrue(repository.BuildManager.add_builds.called)
        self.assertFalse(repository.ui_notifications.publish.called)
        self.assertEqual(self.repo.url, repo.url)

    @patch.object(repository, 'get_poller_client', MagicMock())
    @patch.object(repository.BuildManager, 'add_builds', AsyncMock(
        spec=repository.BuildManager.add_builds))
    @patch.object(repository.ui_notifications, 'publish', AsyncMock(
        spec=repository.ui_notifications.publish))
    @async_test
    async def test_update_code_without_revisions(self):
        repository.get_poller_client.return_value.__aenter__.return_value = \
            AsyncMock(poll_repo=AsyncMock(
                return_value={'revisions': [],
                              'clone_status': 'success',
                              'with_clone': False}))

        await self.repo.update_code()
        self.assertFalse(repository.BuildManager.add_builds.called)
        self.assertFalse(repository.ui_notifications.publish.called)

    @patch.object(repository, 'get_poller_client', MagicMock())
    @patch.object(repository.BuildManager, 'add_builds', AsyncMock(
        spec=repository.BuildManager.add_builds))
    @patch.object(repository.ui_notifications, 'publish', AsyncMock(
        spec=repository.ui_notifications.publish))
    @async_test
    async def test_update_code_with_clone(self):
        repository.get_poller_client.return_value.__aenter__.return_value = \
            AsyncMock(poll_repo=AsyncMock(
                return_value={
                    'revisions': [
                        {
                            'commit': 'adsf',
                            'branch': 'master',
                            'commit_date': '4 04 25 23:49:19 2019 +0000',
                            'author': 'me',
                            'title': 'zhe-commit'}],
                    'clone_status': 'clone-exception',
                    'with_clone': True}))
        await self.repo.update_code()
        await self.repo.reload()
        self.assertEqual(self.repo.clone_status, 'clone-exception')
        self.assertTrue(repository.BuildManager.add_builds.called)
        self.assertTrue(repository.ui_notifications.publish.called)

    @async_test
    async def test_bootstrap(self):
        self.repo.schedule = Mock()
        await self.repo.bootstrap()
        self.assertTrue(self.repo.schedule.called)

    @patch.object(repository.Repository, 'bootstrap', AsyncMock())
    @async_test
    async def test_bootstrap_all(self):
        await repository.Repository.bootstrap_all()
        self.assertTrue(repository.Repository.bootstrap.called)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMock())
    def test_schedule(self):
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        self.repo.schedule()

        self.assertTrue(self.repo.scheduler.add.called)
        self.assertTrue(repository._update_code_hashes)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMock())
    def test_schedule_no_poller(self):
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        self.repo.schedule_poller = False
        self.repo.schedule()

        self.assertTrue(self.repo.scheduler.add.called)
        self.assertFalse(repository._update_code_hashes)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMock())
    @patch('toxicbuild.master.scheduler')
    @async_test
    async def test_schedule_all(self, *a, **kw):
        # await self._create_db_revisions()
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        await self.repo.schedule_all()
        from toxicbuild.master import scheduler
        self.assertTrue(scheduler.add.called)

    @async_test
    async def test_add_slave(self):
        # await self._create_db_revisions()
        slave = await repository.Slave.create(name='name',
                                              host='127.0.0.1',
                                              port=7777,
                                              token='123',
                                              owner=self.owner)

        await self.repo.add_slave(slave)
        slaves = await self.repo.slaves
        self.assertEqual(len(slaves), 2)

    @async_test
    async def test_remove_slave(self):
        # await self._create_db_revisions()
        slave = await repository.Slave.create(name='name',
                                              host='127.0.0.1',
                                              port=7777,
                                              token='123',
                                              owner=self.owner)
        await self.repo.add_slave(slave)
        await self.repo.remove_slave(slave)

        self.assertEqual(len((await self.repo.slaves)), 1)

    @async_test
    async def test_add_branch(self):
        # await self._create_db_revisions()
        await self.repo.add_or_update_branch('master')
        self.assertEqual(len(self.repo.branches), 1)

    @async_test
    async def test_update_branch(self):
        await self.repo.add_or_update_branch('master')
        await self.repo.add_or_update_branch('other-branch')
        await self.repo.add_or_update_branch('master', True)
        repo = await repository.Repository.get(id=self.repo.id)
        self.assertTrue(repo.branches[0].notify_only_latest)
        self.assertEqual(len(repo.branches), 2)

    @async_test
    async def test_remove_branch(self):
        await self.repo.add_or_update_branch('master')
        await self.repo.remove_branch('master')
        self.assertTrue(len(self.repo.branches), 0)

    @async_test
    async def test_get_latest_revision_for_branch(self):
        # await self._create_db_revisions()
        expected = '123asdf1'
        rev = await self.repo.get_latest_revision_for_branch('master')
        self.assertEqual(expected, rev.commit)

    @async_test
    async def test_get_latest_revision_for_branch_without_revision(self):
        rev = await self.repo.get_latest_revision_for_branch('nonexistant')
        self.assertIsNone(rev)

    @async_test
    async def test_get_latest_revisions(self):
        revs = await self.repo.get_latest_revisions()

        self.assertEqual(revs['master'].commit, '123asdf1')
        self.assertEqual(revs['dev'].commit, '123asdf1')

    @async_test
    async def test_get_known_branches(self):
        expected = ['master', 'dev']
        returned = await self.repo.get_known_branches()

        self.assertTrue(expected, returned)

    @async_test
    async def test_add_revision(self):
        await self.repo.save()
        branch = 'master'
        commit = 'asdf213'
        commit_date = datetime.datetime.now()
        kw = {'commit': commit, 'commit_date': commit_date,
              'author': 'someone', 'title': 'uhuuu!!'}
        rev = await self.repo.add_revision(branch, **kw)
        self.assertTrue(rev.id)
        self.assertEqual('uhuuu!!', rev.title)

    @async_test
    async def test_add_revision_external(self):
        await self.repo.save()
        branch = 'master'
        commit = 'asdf213'
        commit_date = datetime.datetime.now()
        kw = {'commit': commit, 'commit_date': commit_date,
              'author': 'someone', 'title': 'uhuuu!!'}
        external = {'url': 'http://bla.com/bla.git', 'name': 'remote',
                    'branch': 'master', 'into': 'bla'}
        rev = await self.repo.add_revision(branch, external=external, **kw)
        self.assertTrue(rev.id)
        self.assertEqual('uhuuu!!', rev.title)
        self.assertTrue(rev.external)

    @async_test
    async def test_add_builds_for_buildset(self):
        await self.repo.save()
        add_builds_for = AsyncMock(
            spec=self.repo.build_manager.add_builds_for_buildset)
        self.repo.build_manager.add_builds_for_buildset = add_builds_for

        buildset = MagicMock()
        builders = [MagicMock()]
        conf = Mock()
        args = (buildset, conf)

        await self.repo.add_builds_for_buildset(*args, builders=builders)

        called_args = add_builds_for.call_args[0]

        self.assertEqual(called_args, args)
        called_kw = add_builds_for.call_args[1]
        self.assertEqual(called_kw['builders'], builders)

    @patch.object(build.BuildSet, 'notify', AsyncMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_with_running_build(self):

        running_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='running', builder=self.builder)
        buildset = await build.BuildSet.create(repository=self.repo,
                                               revision=self.revs[0])
        buildset.builds.append(running_build)
        await buildset.save()
        await buildset.update_status()
        await self.repo.set_latest_buildset(buildset)
        self.assertEqual((await self.repo.get_status()), 'running')

    @patch.object(build.BuildSet, 'notify', AsyncMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_with_success_build(self):

        success_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='success', builder=self.builder)

        builds = [success_build]
        for i, b in enumerate(builds):
            buildset = await build.BuildSet.create(repository=self.repo,
                                                   revision=self.revs[i])
            buildset.builds.append(b)
            await buildset.save()
            await buildset.update_status()

        await self.repo.set_latest_buildset(buildset)
        status = await self.repo.get_status()
        self.assertEqual(status, 'success')

    @patch.object(build.BuildSet, 'notify', AsyncMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_with_fail_build(self):

        fail_build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='master',
                                 started=datetime.datetime.now(),
                                 status='fail', builder=self.builder)
        buildset = await build.BuildSet.create(repository=self.repo,
                                               revision=self.revs[0])

        buildset.builds.append(fail_build)
        await buildset.save()
        await buildset.update_status()
        await self.repo.set_latest_buildset(buildset)
        self.assertEqual((await self.repo.get_status()), 'fail')

    @async_test
    async def test_get_status_cloning_repo(self):
        self.repo.clone_status = 'cloning'
        status = await self.repo.get_status()
        self.assertEqual(status, 'cloning')

    @async_test
    async def test_get_status_clone_exception(self):
        self.repo.clone_status = 'clone-exception'
        status = await self.repo.get_status()
        self.assertEqual(status, 'clone-exception')

    @async_test
    async def test_get_status_without_build(self):

        self.assertEqual((await self.repo.get_status()), 'ready')

    @patch.object(build.BuildSet, 'notify', AsyncMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_only_pending(self):

        p_build = build.Build(repository=self.repo, slave=self.slave,
                              branch='master', named_tree='master',
                              started=datetime.datetime.now(),
                              builder=self.builder)

        p1_build = build.Build(repository=self.repo, slave=self.slave,
                               branch='master', named_tree='v0.1',
                               builder=self.builder)
        builds = [p_build, p1_build]
        for i, b in enumerate(builds):
            buildset = await build.BuildSet.create(repository=self.repo,
                                                   revision=self.revs[i])

            buildset.builds.append(b)
            await buildset.save()

        self.assertEqual((await self.repo.get_status()), 'ready')

    @patch.object(build.BuildSet, 'notify', AsyncMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_only_no_config(self):

        p_build = build.Build(repository=self.repo, slave=self.slave,
                              branch='master', named_tree='master',
                              started=datetime.datetime.now(),
                              builder=self.builder)

        p1_build = build.Build(repository=self.repo, slave=self.slave,
                               branch='master', named_tree='v0.1',
                               builder=self.builder)
        builds = [p_build, p1_build]
        for i, b in enumerate(builds):
            buildset = await build.BuildSet.create(repository=self.repo,
                                                   revision=self.revs[i])
            buildset.status = 'no config'

            buildset.builds.append(b)
            await buildset.save()

        self.assertEqual((await self.repo.get_status()), 'ready')

    @async_test
    async def test_get_builders(self):
        await self._create_db_revisions()
        self.repo.build_manager.get_builders = AsyncMock(
            spec=self.repo.build_manager.get_builders, autospec=True)
        self.repo.build_manager.get_builders.return_value = [self.builder], \
            'master'
        conf = MagicMock()
        builders, origin = await self.repo._get_builders(self.revision,
                                                         conf)
        self.assertEqual(builders, [self.builder])

    def test_get_builder_kw_name(self):
        name_or_id = 'a-name'
        expected = {'name': 'a-name', 'repository': self.repo}
        r = self.repo._get_builder_kw(name_or_id)

        self.assertEqual(r, expected)

    def test_get_builder_kw_id(self):
        name_or_id = repository.ObjectId()
        expected = {
            'id': name_or_id,
            'repository': self.repo
        }
        r = self.repo._get_builder_kw(name_or_id)

        self.assertEqual(r, expected)

    @patch.object(build.notifications, 'publish',
                  AsyncMock(spec=build.notifications.publish))
    @patch.object(build.integrations_notifications, 'publish',
                  AsyncMock(spec=build.integrations_notifications.publish))
    @async_test
    async def test_start_build(self):
        await self._create_db_revisions()

        self.repo.get_config_for = MagicMock(
            spec=self.repo.get_config_for)
        self.repo.add_builds_for_buildset = AsyncMock(
            spec=self.repo.add_builds_for_buildset)
        self.repo.get_latest_revision_for_branch = AsyncMock(
            spec=self.repo.get_latest_revision_for_branch)
        self.repo.get_latest_revision_for_branch.return_value = self.revision
        self.repo._get_builders = AsyncMock(spec=self.repo._get_builders)
        self.repo._get_builders.return_value = {self.slave: ['bla']}, 'master'

        await self.repo.start_build('master')

        self.assertTrue(self.repo.add_builds_for_buildset.called)
        self.assertTrue(self.repo.get_latest_revision_for_branch.called)
        self.assertTrue(self.repo._get_builders.called)

    @async_test
    async def test_start_build_params(self):
        await self._create_db_revisions()

        self.repo.get_config_for = MagicMock(
            spec=self.repo.get_config_for)
        self.repo.add_builds_for_buildset = AsyncMock(
            spec=self.repo.add_builds_for_buildset)
        self.repo.get_latest_revision_for_branch = AsyncMock(
            spec=self.repo.get_latest_revision_for_branch)
        self.repo.get_latest_revision_for_branch.return_value = self.revision
        self.repo._get_builders = AsyncMock(
            spec=self.repo._get_builders)

        await self.repo.start_build('master', builder_name_or_id='builder0',
                                    named_tree='asdf')

        self.assertTrue(self.repo.add_builds_for_buildset.called)
        self.assertFalse(self.repo.get_latest_revision_for_branch.called)
        self.assertFalse(self.repo._get_builders.called)

    @patch.object(repository.buildset_added, 'send', Mock(
        spec=repository.buildset_added.send))
    @async_test
    async def test_start_build_no_conf(self):
        await self._create_db_revisions()
        self.revs[0].config = None
        await self.revs[0].save()
        self.repo.add_builds_for_buildset = AsyncMock(
            spec=self.repo.add_builds_for_buildset)

        await repository.RepositoryRevision.objects.update(set__config=None)

        await self.repo.start_build('master', builder_name_or_id='builder0',
                                    named_tree=self.revs[0].commit)

        self.assertFalse(self.repo.add_builds_for_buildset.called)
        self.assertTrue(repository.buildset_added.send.called)

    @patch.object(repository, 'notifications', AsyncMock(
        spec=repository.notifications))
    @async_test
    async def test_request_build(self):
        branch = 'master'
        named_tree = 'asfd1234'

        await self.repo.request_build(branch, named_tree=named_tree)
        self.assertTrue(repository.notifications.publish.called)

    def test_add_running_build(self):
        repository.Repository.add_running_build()
        self.assertEqual(repository.Repository.get_running_builds(), 1)

    def test_remove_running_build(self):
        repository.Repository.add_running_build()
        repository.Repository.remove_running_build()
        self.assertEqual(repository.Repository.get_running_builds(), 0)

    @async_test
    async def test_cancel_build(self):
        self.repo.build_manager.cancel_build = AsyncMock(
            spec=self.repo.build_manager.cancel_build)
        await self.repo.cancel_build('some-uuid')
        self.assertTrue(self.repo.build_manager.cancel_build.called)

    def test_notify_only_latest(self):
        self.repo.branches = [repository.RepositoryBranch(
            name='master', notify_only_latest=False)]
        only_latest = self.repo.notify_only_latest('master')
        self.assertFalse(only_latest)

    def test_notify_only_latest_not_known(self):
        self.repo.branches = [repository.RepositoryBranch(
            name='master', notify_only_latest=False)]
        only_latest = self.repo.notify_only_latest('dont-know')
        self.assertTrue(only_latest)

    @async_test
    async def test_enable(self):
        self.repo.enabled = False
        await self.repo.save()
        await self.repo.enable()
        self.assertTrue(self.repo.enabled)

    @async_test
    async def test_disable(self):
        self.repo.enabled = True
        await self.repo.save()
        await self.repo.disable()
        self.assertFalse(self.repo.enabled)

    def test_get_config_for(self):
        self.revs[0].config = 'language: python'
        r = self.repo.get_config_for(self.revs[0])
        self.assertTrue(r)

    @async_test
    async def test_add_envvars(self):
        await self._create_db_revisions()
        await self.repo.add_envvars(**{'BLA': 'oi'})
        await self.repo.reload()

        self.assertEqual(self.repo.envvars, {'BLA': 'oi'})

    @async_test
    async def test_rm_envvars(self):
        await self._create_db_revisions()
        await self.repo.add_envvars(**{'BLA': 'oi'})
        await self.repo.rm_envvars(**{'BLA': 'oi', 'BLE': 'nada'})
        await self.repo.reload()

        self.assertEqual(self.repo.envvars, {})

    @async_test
    async def test_replace_envvars(self):
        await self._create_db_revisions()
        await self.repo.add_envvars(**{'BLA': 'oi'})
        await self.repo.replace_envvars(**{'BLE': 'OI'})
        await self.repo.reload()

        self.assertEqual(self.repo.envvars, {'BLE': 'OI'})

    @patch.object(repository, 'get_secrets_client', MagicMock())
    @async_test
    async def test_add_or_update_secret(self):
        client = AsyncMock()
        repository.get_secrets_client.return_value\
                                     .__aenter__.return_value = client
        await self.repo.add_or_update_secret('something', 'very secret')
        self.assertTrue(client.add_or_update_secret.called)

    @patch.object(repository, 'get_secrets_client', MagicMock())
    @async_test
    async def test_rm_secret(self):
        client = AsyncMock()
        repository.get_secrets_client.return_value\
                                     .__aenter__.return_value = client
        await self.repo.rm_secret('something')
        self.assertTrue(client.remove_secret.called)

    @patch.object(repository, 'get_secrets_client', MagicMock())
    @async_test
    async def test_get_secrets(self):
        client = AsyncMock()
        repository.get_secrets_client.return_value\
                                     .__aenter__.return_value = client
        r = await self.repo.get_secrets()
        self.assertIs(client.get_secrets.return_value, r)

    @patch.object(repository, 'get_secrets_client', MagicMock())
    @async_test
    async def test_replace_secrets(self):
        client = AsyncMock()
        repository.get_secrets_client.return_value\
                                     .__aenter__.return_value = client
        await self.repo.replace_secrets(**{'a': 'b', 'c': 'd'})
        self.assertTrue(client.remove_all.called)
        self.assertEqual(len(client.add_or_update_secret.call_args_list), 2)


class RepositoryBranchTest(TestCase):

    def test_to_dict(self):
        branch = repository.RepositoryBranch(name='master')
        branch_dict = branch.to_dict()
        self.assertTrue(branch_dict['name'])


class RepositoryRevisionTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = users.User(email='a@a.com', password='bla')
        await self.user.save()
        self.repo = repository.Repository(name='bla', url='bla@bl.com/aaa',
                                          owner=self.user)
        await self.repo.save()
        self.rev = repository.RepositoryRevision(repository=self.repo,
                                                 commit='asdfasf',
                                                 branch='master',
                                                 author='ze',
                                                 title='bla',
                                                 commit_date=utils.now())
        await self.rev.save()

    @async_test
    async def tearDown(self):
        await repository.RepositoryRevision.drop_collection()
        await repository.Repository.drop_collection()
        await users.User.drop_collection()

    @async_test
    async def test_get(self):
        r = await repository.RepositoryRevision.get(
            commit='asdfasf', repository=self.repo)
        self.assertEqual(r, self.rev)

    @async_test
    async def test_to_dict(self):
        expected = {'repository_id': str(self.repo.id),
                    'commit': self.rev.commit,
                    'branch': self.rev.branch,
                    'author': self.rev.author,
                    'title': self.rev.title,
                    'commit_date': repository.utils.datetime2string(
                        self.rev.commit_date)}
        returned = await self.rev.to_dict()
        self.assertEqual(expected, returned)

    @async_test
    async def test_to_dict_external(self):
        ext = repository.ExternalRevisionIinfo(
            url='http://someurl.com/bla.git', name='other-remote',
            branch='master', into='other-remote:master')
        self.rev.external = ext
        await self.rev.save()
        expected = {'repository_id': str(self.repo.id),
                    'commit': self.rev.commit,
                    'branch': self.rev.branch,
                    'author': self.rev.author,
                    'title': self.rev.title,
                    'commit_date': repository.utils.datetime2string(
                        self.rev.commit_date),
                    'external': {'branch': 'master',
                                 'name': 'other-remote',
                                 'url': 'http://someurl.com/bla.git',
                                 'into': 'other-remote:master'}}
        returned = await self.rev.to_dict()
        self.assertEqual(expected, returned)

    def test_check_skip(self):
        self.rev.body = 'some body\nhey you ci: skip please'
        self.assertFalse(self.rev.create_builds())

    def test_check_skip_dont_skip(self):
        self.rev.body = 'some body\n'
        self.assertTrue(self.rev.create_builds())

    def test_get_builders_conf_include(self):
        self.rev.body = 'some body\nci: include-builders a-builder, o-builder'
        expected = {
            'include': ['a-builder', 'o-builder'],
            'exclude': []
        }
        builders = self.rev.get_builders_conf()
        self.assertEqual(builders, expected)

    def test_get_builders_conf_exclude(self):
        self.rev.body = 'some body\nci: exclude-builders a-builder, o-builder'
        expected = {
            'include': [],
            'exclude': ['a-builder', 'o-builder'],
        }
        builders = self.rev.get_builders_conf()
        self.assertEqual(builders, expected)
