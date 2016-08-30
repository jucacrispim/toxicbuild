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
from tests import async_test


class RepositoryTest(TestCase):

    def setUp(self):
        super(RepositoryTest, self).setUp()
        self.repo = repository.Repository(
            name='reponame', url="git@somewhere.com/project.git",
            vcs_type='git', update_seconds=100, clone_status='done')

    @async_test
    def tearDown(self):
        yield from repository.Repository.drop_collection()
        yield from repository.RepositoryRevision.drop_collection()
        yield from slave.Slave.drop_collection()
        yield from build.Builder.drop_collection()
        super(RepositoryTest, self).tearDown()

    @async_test
    def test_to_dict(self):
        yield from self._create_db_revisions()
        d = yield from self.repo.to_dict()
        self.assertTrue(d['id'])

    @async_test
    def test_to_dict_id_as_str(self):
        yield from self._create_db_revisions()
        d = yield from self.repo.to_dict(True)
        self.assertIsInstance(d['id'], str)

    def test_workdir(self):
        expected = 'src/git-somewhere.com-project.git'
        self.assertEqual(self.repo.workdir, expected)

    def test_poller(self):
        self.assertEqual(type(self.repo.poller), repository.Poller)

    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    def test_create(self):
        slave_inst = yield from slave.Slave.create(name='name', host='bla.com',
                                                   port=1234, token='123')
        repo = yield from repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git', slaves=[slave_inst])

        self.assertTrue(repo.id)
        slaves = yield from repo.slaves
        self.assertEqual(slaves[0], slave_inst)

    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    def test_create_with_branches(self):
        slave_inst = yield from slave.Slave.create(name='name', host='bla.com',
                                                   port=1234, token='123;_')
        branches = [repository.RepositoryBranch(name='branch{}'.format(str(i)),
                                                notify_only_latest=bool(i))
                    for i in range(3)]

        repo = yield from repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git', slaves=[slave_inst],
            branches=branches)

        self.assertTrue(repo.id)
        self.assertEqual(len(repo.branches), 3)

    @patch.object(repository, 'shutil', Mock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    def test_remove(self):
        repo = yield from repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git')
        repo.schedule()
        builder = repository.Builder(name='b1', repository=repo)
        yield from builder.save()
        yield from repo.remove()

        builders_count = yield from repository.Builder.objects.filter(
            repository=repo).count()

        self.assertEqual(builders_count, 0)

        with self.assertRaises(repository.Repository.DoesNotExist):
            yield from repository.Repository.get(url=repo.url)

        self.assertIsNone(repository._scheduler_hashes.get(repo.url))
        self.assertIsNone(repository._scheduler_hashes.get(
            '{}-start-pending'.format(repo.url)))

    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    def test_get(self):
        slave_inst = yield from slave.Slave.create(name='name', host='bla.com',
                                                   port=1234, token='123')
        old_repo = yield from repository.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git', slaves=[slave_inst])
        new_repo = yield from repository.Repository.get(url=old_repo.url)

        slaves = yield from new_repo.slaves
        self.assertEqual(old_repo, new_repo)
        self.assertEqual(slaves[0], slave_inst)

    @async_test
    def test_update_code_with_clone_exception(self):
        self.repo._poller_instance = MagicMock()
        yield from self.repo.save()
        self.repo._poller_instance.poll.side_effect = CloneException
        yield from self.repo.update_code()
        self.assertEqual(self.repo.clone_status, 'clone-exception')

    @async_test
    def test_update_code(self):
        self.repo.clone_status = 'cloning'
        yield from self.repo.save()
        self.repo._poller_instance = MagicMock()

        yield from self.repo.update_code()
        self.assertEqual(self.repo.clone_status, 'done')

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository, 'scheduler', Mock(
        spec=repository.scheduler))
    def test_schedule(self):
        self.repo.schedule()

        self.assertTrue(repository.scheduler.add.called)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository, 'scheduler', Mock(
        spec=repository.scheduler))
    @async_test
    def test_schedule_all(self):
        yield from self._create_db_revisions()
        yield from self.repo.schedule_all()

        self.assertTrue(repository.scheduler.add.called)

    @async_test
    def test_add_slave(self):
        yield from self._create_db_revisions()
        slave = yield from repository.Slave.create(name='name',
                                                   host='127.0.0.1',
                                                   port=7777,
                                                   token='123')

        yield from self.repo.add_slave(slave)
        slaves = yield from self.repo.slaves
        self.assertEqual(len(slaves), 1)

    @async_test
    def test_remove_slave(self):
        yield from self._create_db_revisions()
        slave = yield from repository.Slave.create(name='name',
                                                   host='127.0.0.1',
                                                   port=7777,
                                                   token='123')
        yield from self.repo.add_slave(slave)
        yield from self.repo.remove_slave(slave)

        self.assertEqual(len((yield from self.repo.slaves)), 0)

    @async_test
    def test_add_branch(self):
        yield from self.repo.add_or_update_branch('master')
        self.assertEqual(len(self.repo.branches), 1)

    @async_test
    def test_update_branch(self):
        yield from self.repo.add_or_update_branch('master')
        yield from self.repo.add_or_update_branch('other-branch')
        yield from self.repo.add_or_update_branch('master', True)
        repo = yield from repository.Repository.get(id=self.repo.id)
        self.assertTrue(repo.branches[0].notify_only_latest)
        self.assertEqual(len(repo.branches), 2)

    @async_test
    def test_remove_branch(self):
        yield from self.repo.add_or_update_branch('master')
        yield from self.repo.remove_branch('master')
        self.assertTrue(len(self.repo.branches), 0)

    @async_test
    def test_get_latest_revision_for_branch(self):
        yield from self._create_db_revisions()
        expected = '123asdf1'
        rev = yield from self.repo.get_latest_revision_for_branch('master')
        self.assertEqual(expected, rev.commit)

    @async_test
    def test_get_latest_revision_for_branch_without_revision(self):
        yield from self._create_db_revisions()
        rev = yield from self.repo.get_latest_revision_for_branch(
            'nonexistant')
        self.assertIsNone(rev)

    @async_test
    def test_get_latest_revisions(self):
        yield from self._create_db_revisions()
        revs = yield from self.repo.get_latest_revisions()

        self.assertEqual(revs['master'].commit, '123asdf1')
        self.assertEqual(revs['dev'].commit, '123asdf1')

    @async_test
    def test_get_known_branches(self):
        yield from self._create_db_revisions()
        expected = ['master', 'dev']
        returned = yield from self.repo.get_known_branches()

        self.assertTrue(expected, returned)

    @async_test
    def test_add_revision(self):
        yield from self.repo.save()
        branch = 'master'
        commit = 'asdf213'
        commit_date = datetime.datetime.now()
        kw = {'commit': commit, 'commit_date': commit_date,
              'author': 'someone', 'title': 'uhuuu!!'}
        rev = yield from self.repo.add_revision(branch, **kw)
        self.assertTrue(rev.id)
        self.assertEqual('uhuuu!!', rev.title)

    @async_test
    def test_add_builds_for_slave(self):
        yield from self.repo.save()
        self.repo.build_manager.add_builds_for_slave = MagicMock(
            spec=build.BuildManager.add_builds_for_slave)

        buildset = MagicMock()
        slave = MagicMock()
        builders = [MagicMock()]
        args = (buildset, slave)

        yield from self.repo.add_builds_for_slave(*args, builders=builders)

        called_args = self.repo.build_manager.add_builds_for_slave.call_args[0]

        self.assertEqual(called_args, args)
        called_kw = self.repo.build_manager.add_builds_for_slave.call_args[1]
        self.assertEqual(called_kw['builders'], builders)

    @async_test
    def test_get_status_with_running_build(self):
        yield from self._create_db_revisions()

        running_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='running', builder=self.builder)
        buildset = yield from build.BuildSet.create(repository=self.repo,
                                                    revision=self.revs[0])

        buildset.builds.append(running_build)
        yield from buildset.save()
        self.assertEqual((yield from self.repo.get_status()), 'running')

    @async_test
    def test_get_status_with_success_build(self):
        yield from self._create_db_revisions()

        success_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='success', builder=self.builder)

        pending_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='v0.1',
                                    builder=self.builder)
        builds = [success_build, pending_build]
        for i, b in enumerate(builds):
            buildset = yield from build.BuildSet.create(repository=self.repo,
                                                        revision=self.revs[i])
            buildset.builds.append(b)
            yield from buildset.save()

        self.assertEqual((yield from self.repo.get_status()), 'success')

    @async_test
    def test_get_status_with_fail_build(self):
        yield from self._create_db_revisions()

        fail_build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='master',
                                 started=datetime.datetime.now(),
                                 status='fail', builder=self.builder)
        buildset = yield from build.BuildSet.create(repository=self.repo,
                                                    revision=self.revs[0])

        buildset.builds.append(fail_build)
        yield from buildset.save()
        self.assertEqual((yield from self.repo.get_status()), 'fail')

    @async_test
    def test_get_status_cloning_repo(self):
        yield from self._create_db_revisions()
        self.repo.clone_status = 'cloning'
        status = yield from self.repo.get_status()
        self.assertEqual(status, 'cloning')

    @async_test
    def test_get_status_clone_exception(self):
        yield from self._create_db_revisions()
        self.repo.clone_status = 'clone-exception'
        status = yield from self.repo.get_status()
        self.assertEqual(status, 'clone-exception')

    @async_test
    def test_get_status_without_build(self):
        yield from self._create_db_revisions()

        self.assertEqual((yield from self.repo.get_status()), 'idle')

    @async_test
    def test_get_status_only_pending(self):
        yield from self._create_db_revisions()

        p_build = build.Build(repository=self.repo, slave=self.slave,
                              branch='master', named_tree='master',
                              started=datetime.datetime.now(),
                              builder=self.builder)

        p1_build = build.Build(repository=self.repo, slave=self.slave,
                               branch='master', named_tree='v0.1',
                               builder=self.builder)
        builds = [p_build, p1_build]
        for i, b in enumerate(builds):
            buildset = yield from build.BuildSet.create(repository=self.repo,
                                                        revision=self.revs[i])

            buildset.builds.append(b)
            yield from buildset.save()

        self.assertEqual((yield from self.repo.get_status()), 'idle')

    @patch.object(repository, 'repo_status_changed', Mock())
    @async_test
    def test_check_for_status_change_not_changing(self):
        self.repo._old_status = 'running'

        @asyncio.coroutine
        def get_status():
            return 'running'

        self.repo.get_status = get_status

        yield from self.repo._check_for_status_change(Mock())
        self.assertFalse(repository.repo_status_changed.send.called)

    @patch.object(repository, 'repo_status_changed', Mock())
    @async_test
    def test_check_for_status_change_changing(self):
        self.repo._old_status = 'running'

        @asyncio.coroutine
        def get_status():
            return 'success'

        self.repo.get_status = get_status

        yield from self.repo._check_for_status_change(Mock())
        self.assertTrue(repository.repo_status_changed.send.called)

    @asyncio.coroutine
    def _create_db_revisions(self):
        yield from self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()
        self.builder = yield from build.Builder.create(name='builder0',
                                                       repository=self.repo)
        self.slave = yield from slave.Slave.create(name='slave',
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

                yield from rev.save()
                self.revs.append(rev)

        # creating another repo just to test the known branches stuff.
        self.other_repo = repository.Repository(name='bla', url='/bla/bla',
                                                update_seconds=300,
                                                vcs_type='git')
        yield from self.other_repo.save()

        for r in range(2):
            for branch in ['b1', 'b2']:
                rev = repository.RepositoryRevision(
                    author='ze',
                    title='commit {}'.format(r),
                    repository=self.other_repo,
                    commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    commit_date=now + datetime.timedelta(r))

                yield from rev.save()


class RepositoryRevisionTest(TestCase):

    @async_test
    def tearDown(self):
        yield from repository.RepositoryRevision.drop_collection()
        yield from repository.Repository.drop_collection()

    @async_test
    def test_get(self):
        repo = repository.Repository(name='bla', url='bla@bl.com/aaa')
        yield from repo.save()
        rev = repository.RepositoryRevision(repository=repo,
                                            commit='asdfasf',
                                            branch='master',
                                            author='ze',
                                            title='bla',
                                            commit_date=utils.now())
        yield from rev.save()
        r = yield from repository.RepositoryRevision.get(
            commit='asdfasf', repository=repo)
        self.assertEqual(r, rev)
