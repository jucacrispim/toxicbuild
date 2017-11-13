# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
from toxicbuild.core import utils
from toxicbuild.master import repository, build, slave
from toxicbuild.master.exceptions import CloneException
from tests import async_test, AsyncMagicMock


class RepoPlugin(repository.MasterPlugin):
    name = 'repo-plugin'
    type = 'test'

    @asyncio.coroutine
    def run(self):
        pass


class RepositoryTest(TestCase):

    def setUp(self):
        super(RepositoryTest, self).setUp()
        self.repo = repository.Repository(
            name='reponame', url="git@somewhere.com/project.git",
            vcs_type='git', update_seconds=100, clone_status='ready')

    @async_test
    async def tearDown(self):
        await repository.Repository.drop_collection()
        await repository.RepositoryRevision.drop_collection()
        await slave.Slave.drop_collection()
        await build.Builder.drop_collection()
        repository.Repository._plugins_instances = {}
        super(RepositoryTest, self).tearDown()

    @async_test
    async def test_to_dict(self):
        await self._create_db_revisions()
        d = await self.repo.to_dict()
        self.assertTrue(d['id'])
        self.assertTrue('plugins' in d.keys())

    @patch.object(repository.Repository, 'update_code', MagicMock())
    @async_test
    async def test_update_repo_code(self):
        update_code = MagicMock(spec=self.repo.update_code)
        repository.Repository.update_code = asyncio.coroutine(
            lambda *a, **kw: update_code(*a, **kw))
        await self._create_db_revisions()
        await repository._update_repo_code(self.repo.id)
        self.assertTrue(update_code.called)

    @async_test
    async def test_to_dict_id_as_str(self):
        await self._create_db_revisions()
        d = await self.repo.to_dict(True)
        self.assertIsInstance(d['id'], str)

    def test_workdir(self):
        expected = 'src/git-somewhere.com-project.git'
        self.assertEqual(self.repo.workdir, expected)

    def test_poller(self):
        self.assertEqual(type(self.repo.poller), repository.Poller)

    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_create(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                                   port=1234, token='123')
        repo = await repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git', slaves=[slave_inst])

        self.assertTrue(repo.id)
        slaves = await repo.slaves
        self.assertEqual(slaves[0], slave_inst)

    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_create_with_branches(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123;_')
        branches = [repository.RepositoryBranch(name='branch{}'.format(str(i)),
                                                notify_only_latest=bool(i))
                    for i in range(3)]

        repo = await repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git', slaves=[slave_inst],
            branches=branches)

        self.assertTrue(repo.id)
        self.assertEqual(len(repo.branches), 3)

    @patch.object(repository, 'shutil', Mock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_remove(self):
        repo = await repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git')
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

    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_get(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                                   port=1234, token='123')
        old_repo = await repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git', slaves=[slave_inst])
        new_repo = await repository.Repository.get(url=old_repo.url)

        slaves = await new_repo.slaves
        self.assertEqual(old_repo, new_repo)
        self.assertEqual(slaves[0], slave_inst)

    @async_test
    async def test_update_code_with_clone_exception(self):
        self.repo._poller_instance = MagicMock()
        await self.repo.save()
        self.repo._poller_instance.poll.side_effect = CloneException
        await self.repo.update_code()
        self.assertEqual(self.repo.clone_status, 'clone-exception')

    @async_test
    async def test_update_code(self):
        self.repo.clone_status = 'cloning'
        await self.repo.save()
        poller = MagicMock()
        poller.poll = asyncio.coroutine(lambda *a, **kw: False)
        self.repo._poller_instance = poller
        await self.repo.update_code()
        self.assertEqual(self.repo.clone_status, 'ready')

    @patch.object(repository, 'repo_status_changed', Mock())
    @async_test
    async def test_update_with_clone_sending_signal(self):
        self.repo.clone_status = 'cloning'
        await self.repo.save()
        self.repo._poller_instance = MagicMock()
        self.repo._poller_instance.poll = asyncio.coroutine(lambda: True)
        await self.repo.update_code()
        self.assertTrue(repository.repo_status_changed.send.called)

    @patch.object(repository.utils, 'log', Mock())
    def test_schedule(self):
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        plugin = MagicMock
        plugin.name = 'my-plugin'
        plugin.run = AsyncMagicMock()
        self.repo.plugins = [plugin]
        self.repo.schedule()

        self.assertTrue(self.repo.scheduler.add.called)
        self.assertTrue(self.repo.plugins[0].called)

    @patch.object(repository.utils, 'log', Mock())
    @patch('toxicbuild.master.scheduler')
    @async_test
    async def test_schedule_all(self, *a, **kw):
        await self._create_db_revisions()
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        await self.repo.schedule_all()
        from toxicbuild.master import scheduler
        self.assertTrue(scheduler.add.called)

    @async_test
    async def test_add_slave(self):
        await self._create_db_revisions()
        slave = await repository.Slave.create(name='name',
                                              host='127.0.0.1',
                                              port=7777,
                                              token='123')

        await self.repo.add_slave(slave)
        slaves = await self.repo.slaves
        self.assertEqual(len(slaves), 1)

    @async_test
    async def test_remove_slave(self):
        await self._create_db_revisions()
        slave = await repository.Slave.create(name='name',
                                              host='127.0.0.1',
                                              port=7777,
                                              token='123')
        await self.repo.add_slave(slave)
        await self.repo.remove_slave(slave)

        self.assertEqual(len((await self.repo.slaves)), 0)

    @async_test
    async def test_add_branch(self):
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
        await self._create_db_revisions()
        expected = '123asdf1'
        rev = await self.repo.get_latest_revision_for_branch('master')
        self.assertEqual(expected, rev.commit)

    @async_test
    async def test_get_latest_revision_for_branch_without_revision(self):
        await self._create_db_revisions()
        rev = await self.repo.get_latest_revision_for_branch('nonexistant')
        self.assertIsNone(rev)

    @async_test
    async def test_get_latest_revisions(self):
        await self._create_db_revisions()
        revs = await self.repo.get_latest_revisions()

        self.assertEqual(revs['master'].commit, '123asdf1')
        self.assertEqual(revs['dev'].commit, '123asdf1')

    @async_test
    async def test_get_known_branches(self):
        await self._create_db_revisions()
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

    def test_run_plugin(self):
        plugin = MagicMock()
        plugin.name = 'my-plugin'
        plugin.run = AsyncMagicMock()
        expected_key = '{}-plugin-{}'.format(self.repo.url, plugin.name)
        self.repo._run_plugin(plugin)
        self.assertTrue(plugin.run.called)
        self.assertIn(
            expected_key, repository.Repository._plugins_instances.keys())

    def test_stop_plugin(self):
        plugin = MagicMock()
        plugin.name = 'my-plugin'
        plugin.run = AsyncMagicMock()
        plugin.stop = AsyncMagicMock()
        self.repo._run_plugin(plugin)
        self.repo._stop_plugin(plugin)
        self.assertTrue(plugin.stop.called)
        self.assertFalse(repository.Repository._plugins_instances)

    @async_test
    async def test_enable_plugin(self):
        await self.repo.save()
        await self.repo.enable_plugin('repo-plugin')
        self.assertEqual(len(self.repo.plugins), 1)

    def test_match_kw(self):
        plugin = repository.MasterPlugin()
        kw = {'name': 'BaseMasterPlugin', 'type': None}
        match = self.repo._match_kw(plugin, **kw)
        self.assertTrue(match)

    def test_match_not_matching(self):
        plugin = repository.MasterPlugin()
        kw = {'name': 'BaseMasterPlugin', 'type': 'bla'}
        match = self.repo._match_kw(plugin, **kw)
        self.assertFalse(match)

    def test_test_match_bad_attr(self):
        plugin = repository.MasterPlugin()
        kw = {'name': 'BaseMasterPlugin', 'other': 'ble'}
        match = self.repo._match_kw(plugin, **kw)
        self.assertFalse(match)

    @async_test
    async def test_disable_plugin(self):
        await self.repo.save()
        await self.repo.enable_plugin('repo-plugin')
        kw = {'name': 'repo-plugin'}
        await self.repo.disable_plugin(**kw)
        self.assertEqual(len(self.repo.plugins), 0)

    @async_test
    async def test_add_builds_for_slave(self):
        await self.repo.save()
        add_builds_for_slave = MagicMock(
            spec=build.BuildManager.add_builds_for_slave)
        self.repo.build_manager.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))

        buildset = MagicMock()
        slave = MagicMock()
        builders = [MagicMock()]
        args = (buildset, slave)

        await self.repo.add_builds_for_slave(*args, builders=builders)

        called_args = add_builds_for_slave.call_args[0]

        self.assertEqual(called_args, args)
        called_kw = add_builds_for_slave.call_args[1]
        self.assertEqual(called_kw['builders'], builders)

    @async_test
    async def test_get_status_with_running_build(self):
        await self._create_db_revisions()

        running_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='running', builder=self.builder)
        buildset = await build.BuildSet.create(repository=self.repo,
                                               revision=self.revs[0])

        buildset.builds.append(running_build)
        await buildset.save()
        self.assertEqual((await self.repo.get_status()), 'running')

    @async_test
    async def test_get_status_with_success_build(self):
        await self._create_db_revisions()

        success_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='success', builder=self.builder)

        pending_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='v0.1',
                                    builder=self.builder)
        builds = [success_build, pending_build]
        for i, b in enumerate(builds):
            buildset = await build.BuildSet.create(repository=self.repo,
                                                   revision=self.revs[i])
            buildset.builds.append(b)
            await buildset.save()

        self.assertEqual((await self.repo.get_status()), 'success')

    @async_test
    async def test_get_status_with_fail_build(self):
        await self._create_db_revisions()

        fail_build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='master',
                                 started=datetime.datetime.now(),
                                 status='fail', builder=self.builder)
        buildset = await build.BuildSet.create(repository=self.repo,
                                               revision=self.revs[0])

        buildset.builds.append(fail_build)
        await buildset.save()
        self.assertEqual((await self.repo.get_status()), 'fail')

    @async_test
    async def test_get_status_cloning_repo(self):
        await self._create_db_revisions()
        self.repo.clone_status = 'cloning'
        status = await self.repo.get_status()
        self.assertEqual(status, 'cloning')

    @async_test
    async def test_get_status_clone_exception(self):
        await self._create_db_revisions()
        self.repo.clone_status = 'clone-exception'
        status = await self.repo.get_status()
        self.assertEqual(status, 'clone-exception')

    @async_test
    async def test_get_status_without_build(self):
        await self._create_db_revisions()

        self.assertEqual((await self.repo.get_status()), 'ready')

    @async_test
    async def test_get_status_only_pending(self):
        await self._create_db_revisions()

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

    @patch.object(repository, 'repo_status_changed', Mock())
    @async_test
    async def test_check_for_status_change_not_changing(self):
        self.repo._old_status = 'running'

        @asyncio.coroutine
        def get_status():
            return 'running'

        self.repo.get_status = get_status

        await self.repo._check_for_status_change(Mock(), Mock())
        self.assertFalse(repository.repo_status_changed.send.called)

    @patch.object(repository, 'repo_status_changed', Mock())
    @async_test
    async def test_check_for_status_change_changing(self):
        self.repo._old_status = 'running'

        @asyncio.coroutine
        def get_status():
            return 'success'

        self.repo.get_status = get_status

        await self.repo._check_for_status_change(Mock(), Mock())
        self.assertTrue(repository.repo_status_changed.send.called)

    async def _create_db_revisions(self):
        await self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()
        self.builder = await build.Builder.create(name='builder0',
                                                       repository=self.repo)
        self.slave = await slave.Slave.create(name='slave',
                                                   host='localhost',
                                                   port=1234,
                                                   token='asdf')
        self.revs = []

        for r in range(2):
            for branch in ['master', 'dev']:
                rev = repository.RepositoryRevision(
                    repository=rep, commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    author='ze',
                    title='commit {}'.format(r),
                    commit_date=now + datetime.timedelta(r))

                await rev.save()
                self.revs.append(rev)

        # creating another repo just to test the known branches stuff.
        self.other_repo = repository.Repository(name='bla', url='/bla/bla',
                                                update_seconds=300,
                                                vcs_type='git')
        await self.other_repo.save()

        for r in range(2):
            for branch in ['b1', 'b2']:
                rev = repository.RepositoryRevision(
                    author='ze',
                    title='commit {}'.format(r),
                    repository=self.other_repo,
                    commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    commit_date=now + datetime.timedelta(r))

                await rev.save()


class RepositoryBranchTest(TestCase):

    def test_to_dict(self):
        branch = repository.RepositoryBranch(name='master')
        branch_dict = branch.to_dict()
        self.assertTrue(branch_dict['name'])


class RepositoryRevisionTest(TestCase):

    @async_test
    async def tearDown(self):
        await repository.RepositoryRevision.drop_collection()
        await repository.Repository.drop_collection()

    @async_test
    async def test_get(self):
        repo = repository.Repository(name='bla', url='bla@bl.com/aaa')
        await repo.save()
        rev = repository.RepositoryRevision(repository=repo,
                                            commit='asdfasf',
                                            branch='master',
                                            author='ze',
                                            title='bla',
                                            commit_date=utils.now())
        await rev.save()
        r = await repository.RepositoryRevision.get(
            commit='asdfasf', repository=repo)
        self.assertEqual(r, rev)
