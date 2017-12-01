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
from unittest import mock, TestCase
from toxicbuild.master import pollers, repository, users
from toxicbuild.master.exceptions import CloneException
from tests import async_test


class GitPollerTest(TestCase):

    @mock.patch.object(pollers, 'get_vcs', mock.MagicMock())
    @async_test
    async def setUp(self):
        super(GitPollerTest, self).setUp()
        self.owner = users.User(email='a@a.com', password='adsf')
        await self.owner.save()
        self.repo = repository.Repository(
            name='reponame', url='git@somewhere.org/project.git',
            owner=self.owner)

        self.poller = pollers.Poller(
            self.repo, vcs_type='git', workdir='workdir')

    @async_test
    def tearDown(self):
        yield from repository.RepositoryRevision.drop_collection()
        yield from repository.Repository.drop_collection()
        yield from users.User.drop_collection()
        super(GitPollerTest, self).tearDown()

    @mock.patch.object(pollers.revision_added, 'send', mock.Mock())
    def test_notify_changes(self):
        self.poller.notify_change(mock.MagicMock())

        self.assertTrue(pollers.revision_added.send.called)

    @mock.patch.object(pollers.revision_added, 'send', mock.Mock())
    @async_test
    async def test_process_changes(self):
        # now in the future, of course!
        now = datetime.datetime.now() + datetime.timedelta(100)
        branches = [
            repository.RepositoryBranch(name='master',
                                        notify_only_latest=True),
            repository.RepositoryBranch(name='dev',
                                        notify_only_latest=False)]
        self.repo.branches = branches
        await self.repo.save()
        await self._create_db_revisions()

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'zé', 'title': 'sometitle'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'tião', 'title': 'other'}],
                    'dev': [{'commit': 'sdfljfew', 'commit_date': now,
                             'author': 'mariazinha', 'title': 'bla'},
                            {'commit': 'sdlfjslfer3', 'commit_date': now,
                             'author': 'jc', 'title': 'Our lord John Cleese'}],
                    'other': []}

        self.poller.vcs.get_revisions = gr

        await self.poller.process_changes()

        called_revs = pollers.revision_added.send.call_args[1]['revisions']
        # call only 1 because self.poller.notify_only_latest is True
        # for master and call 1 for last revision for dev
        self.assertEqual(len(called_revs), 2)

    @mock.patch.object(pollers.revision_added, 'send', mock.Mock())
    @async_test
    async def test_poll(self):
        await self._create_db_revisions()

        now = datetime.datetime.now()

        def workdir_exists():
            return False

        self.CLONE_CALLED = False

        @asyncio.coroutine
        def clone(url):
            self.CLONE_CALLED = True
            return True

        @asyncio.coroutine
        def has_changes():
            return True

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'eu', 'title': 'something'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'eu', 'title': 'otherthing'}]}

        self.poller.vcs.get_revisions = gr
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.vcs.clone = clone
        self.poller.vcs.has_changes = has_changes

        await self.poller.poll()

        self.assertTrue(self.CLONE_CALLED)

    @mock.patch.object(pollers.revision_added, 'send', mock.Mock())
    @async_test
    async def test_poll_with_clone_exception(self):

        def workdir_exists():
            return False

        @asyncio.coroutine
        def clone(url):
            raise CloneException

        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.log = mock.Mock()
        self.poller.vcs.clone = clone

        with self.assertRaises(CloneException):
            await self.poller.poll()

    @mock.patch.object(pollers.revision_added, 'send', mock.Mock())
    @async_test
    async def test_poll_without_clone(self):
        await self._create_db_revisions()

        now = datetime.datetime.now()

        def workdir_exists():
            return True

        self.CLONE_CALLED = False

        @asyncio.coroutine
        def clone(url):
            self.CLONE_CALLED = True
            return True

        @asyncio.coroutine
        def has_changes():
            return True

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'eu', 'title': 'something'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'eu', 'title': 'bla'}]}

        self.poller.vcs.get_revisions = gr
        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.vcs.clone = clone
        self.poller.vcs.has_changes = has_changes
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: None)

        await self.poller.poll()

        self.assertFalse(self.CLONE_CALLED)

    @mock.patch.object(pollers, 'LoggerMixin', mock.Mock())
    @async_test
    async def test_poll_with_exception_processing_changes(self):
        self.poller.vcs.workdir_exists = mock.Mock(return_value=True)
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.log = mock.Mock()
        self.poller.vcs.process_changes = mock.Mock(side_effect=Exception)
        await self.poller.poll()
        log_level = self.poller.log.call_args[1]['level']
        self.assertEqual(log_level, 'error')

    @async_test
    async def test_poll_with_submodule(self):
        self.poller.process_changes = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.vcs.workdir_exists = lambda: True
        update_submodule = mock.MagicMock(
            spec=self.poller.vcs.update_submodule)
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: update_submodule(*a, **kw))

        await self.poller.poll()

        self.assertTrue(update_submodule.called)

    @async_test
    async def test_poll_already_polling(self):
        self.poller.process_changes = mock.MagicMock()
        self.poller.vcs.workdir_exists = lambda: True
        self.poller.vcs.update_submodule = mock.MagicMock()
        self.poller._is_polling = True
        await self.poller.poll()

        self.assertFalse(self.poller.process_changes.called)

    async def _create_db_revisions(self):
        await self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()

        for r in range(2):
            rev = repository.RepositoryRevision(
                repository=rep, commit='123asdf', branch='master',
                commit_date=now, author='zé', title='algo')

            await rev.save()

            rev = repository.RepositoryRevision(
                repository=rep, commit='123asef', branch='other',
                commit_date=now, author='tião', title='outro')

            await rev.save()
