# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import datetime
from unittest import TestCase
from unittest.mock import patch, Mock, AsyncMock

from toxicbuild.poller import poller

from tests import async_test


@patch('toxicbuild.poller.poller.settings', Mock(SOURCE_CODE_DIR='.'))
class PollerTest(TestCase):

    @patch('toxicbuild.poller.poller.settings', Mock(SOURCE_CODE_DIR='.'))
    def setUp(self):
        repo_id = 'repo-id'
        url = 'https://repo.url/'
        repo_branches = {}
        since = {}
        known_branches = []
        vcs_type = 'git'
        self.poller = poller.Poller(repo_id, url, repo_branches, since,
                                    known_branches, vcs_type)

    @patch.object(poller, 'Lock', Mock(spec=poller.Lock))
    def test_lock_new(self):
        self.assertTrue(self.poller.lock)

    def test_lock(self):
        lock = Mock()
        self.poller._lock = lock
        self.assertIs(self.poller.lock, lock)

    @async_test
    async def test_external_poll(self):
        self.poller.vcs.import_external_branch = AsyncMock(
            spec=self.poller.vcs.import_external_branch)
        self.poller.poll = AsyncMock(spec=self.poller.poll)

        external_url = 'http://ext.url'
        external_name = 'the-name'
        external_branch = 'the-branch'
        into = 'local-branch'
        await self.poller.external_poll(external_url, external_name,
                                        external_branch, into)
        self.assertTrue(self.poller.vcs.import_external_branch.called)
        self.assertTrue(self.poller.poll.called)
        self.assertEqual(self.poller.branches_conf,
                         {'local-branch': {'notify_only_latest': True}})

    @patch.object(poller.LoggerMixin, 'log', Mock(spec=poller.LoggerMixin.log))
    @async_test
    async def test_poll_already_polling(self):
        async with await self.poller.lock.acquire_write():
            r = await self.poller.poll()

        self.assertTrue(r['locked'])

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @async_test
    async def test_poll_clone_exception(self):
        self.poller.vcs.clone = AsyncMock(spec=self.poller.vcs.clone,
                                          side_effect=Exception)
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=False)

        r = await self.poller.poll()
        self.assertTrue(r['clone_error'])

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @patch.object(poller.Poller, 'process_changes', AsyncMock(
        spec=poller.Poller.process_changes, return_value=[Mock(), Mock()]))
    @async_test
    async def test_poll_clone_ok(self):
        self.poller.vcs.clone = AsyncMock(spec=self.poller.vcs.clone)
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=False)
        self.poller.vcs.try_set_remote = AsyncMock(
            spec=self.poller.vcs.try_set_remote)
        self.poller.vcs.update_submodule = AsyncMock(
            spec=self.poller.vcs.update_submodule)

        r = await self.poller.poll()
        self.assertTrue(r['revisions'])
        self.assertTrue(r['with_clone'])

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @patch.object(poller.Poller, 'process_changes', AsyncMock(
        spec=poller.Poller.process_changes, side_effect=Exception))
    @async_test
    async def test_poll_process_changes_exception(self):
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=True)
        self.poller.vcs.try_set_remote = AsyncMock(
            spec=self.poller.vcs.try_set_remote)
        self.poller.vcs.update_submodule = AsyncMock(
            spec=self.poller.vcs.update_submodule)

        r = await self.poller.poll()
        self.assertTrue(r['error'])
        self.assertFalse(r['clone_error'])
        self.assertEqual(len(self.poller.log.call_args_list), 2)

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @patch.object(poller.Poller, 'process_changes', AsyncMock(
        spec=poller.Poller.process_changes, return_value=[Mock(), Mock()]))
    @async_test
    async def test_poll_process_changes_ok(self):
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=True)
        self.poller.vcs.try_set_remote = AsyncMock(
            spec=self.poller.vcs.try_set_remote)
        self.poller.vcs.update_submodule = AsyncMock(
            spec=self.poller.vcs.update_submodule)

        r = await self.poller.poll()
        self.assertTrue(r['revisions'])
        self.assertFalse(r['with_clone'])
        self.assertEqual(len(self.poller.log.call_args_list), 1)

    @patch.object(poller, 'read_file', AsyncMock(
        spec=poller.read_file, side_effect=['config', FileNotFoundError]))
    @patch('toxicbuild.core.vcs.Git.checkout', AsyncMock())
    @async_test
    async def test_process_changes(self):
        # now in the future, of course!a
        now = datetime.datetime.now() + datetime.timedelta(100)
        self.poller.known_branches = ['master']
        branches = {'master': {'notify_only_latest': True}}
        self.poller.branches_conf = branches
        revs = {'master': [{'commit': '123sdf', 'commit_date': now,
                            'author': 'zé', 'title': 'sometitle'},
                           {'commit': 'asdf213', 'commit_date': now,
                            'author': 'tião', 'title': 'other'}],
                'dev': [{'commit': 'sdfljfew', 'commit_date': now,
                         'author': 'mariazinha', 'title': 'bla'},
                        {'commit': 'sdlfjslfer3', 'commit_date': now,
                         'author': 'jc', 'title': 'Our lord John Cleese'}]}

        self.poller.vcs.get_revisions = AsyncMock(return_value=revs)
        r = await self.poller.process_changes()
        self.assertTrue(r)
        self.assertTrue(r[0]['config'])
        self.assertFalse(r[1]['config'])

    @async_test
    async def test_process_changes_no_revisions(self):
        branches = {'master': {'notify_only_latest': True},
                    'dev': {'notify_only_latest': False}}
        self.poller.branches_conf = branches

        self.poller.vcs.get_revisions = AsyncMock(return_value={})

        r = await self.poller.process_changes()

        self.assertFalse(r)

    @patch.object(poller, 'read_file', AsyncMock(spec=poller.read_file,
                                                 return_value='config'))
    @patch('toxicbuild.core.vcs.Git.checkout', AsyncMock())
    @async_test
    async def test_process_changes_local_branch(self):
        now = datetime.datetime.now() + datetime.timedelta(100)
        self.poller.known_branches = ['master']
        branches = {'master': {'notify_only_latest': True}}
        self.poller.branches_conf = branches
        self.poller.local_branch = True
        revs = {'master': [{'commit': '123sdf', 'commit_date': now,
                            'author': 'zé', 'title': 'sometitle'},
                           {'commit': 'asdf213', 'commit_date': now,
                            'author': 'tião', 'title': 'other'}],
                'dev': [{'commit': 'sdfljfew', 'commit_date': now,
                         'author': 'mariazinha', 'title': 'bla'},
                        {'commit': 'sdlfjslfer3', 'commit_date': now,
                         'author': 'jc', 'title': 'Our lord John Cleese'}]}

        self.poller.vcs.get_local_revisions = AsyncMock(return_value=revs)
        r = await self.poller.process_changes()
        self.assertTrue(r)
        self.assertTrue(r[0]['config'])
