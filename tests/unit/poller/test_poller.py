# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import patch, Mock

from toxicbuild.poller import poller

from tests import async_test, AsyncMagicMock


class PollerTest(TestCase):

    def setUp(self):
        repo_id = 'repo-id'
        url = 'https://repo.url/'
        repo_branches = {}
        since = {}
        known_branches = []
        vcs_type = 'git'
        workdir = 'work/dir'
        self.poller = poller.Poller(repo_id, url, repo_branches, since,
                                    known_branches, vcs_type, workdir)

    @patch.object(poller, 'Lock', Mock(spec=poller.Lock))
    def test_lock_new(self):
        self.assertTrue(self.poller.lock)

    def test_lock(self):
        lock = Mock()
        self.poller._lock = lock
        self.assertIs(self.poller.lock, lock)

    @async_test
    async def test_external_poll(self):
        self.poller.vcs.import_external_branch = AsyncMagicMock(
            spec=self.poller.vcs.import_external_branch)
        self.poller.poll = AsyncMagicMock(spec=self.poller.poll)

        external_url = 'http://ext.url'
        external_name = 'the-name'
        external_branch = 'the-branch'
        into = 'local-branch'
        await self.poller.external_poll(external_url, external_name,
                                        external_branch, into)
        self.assertTrue(self.poller.vcs.import_external_branch.called)
        self.assertTrue(self.poller.poll.called)
        self.assertEqual(self.poller.repo_branches, {'local-branch': True})

    @async_test
    async def test_poll_already_polling(self):
        async with await self.poller.lock.acquire_write():
            r = await self.poller.poll()

        self.assertIsNone(r)

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @async_test
    async def test_poll_clone_exception(self):
        self.poller.vcs.clone = AsyncMagicMock(spec=self.poller.vcs.clone,
                                               side_effect=Exception)
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=False)

        with self.assertRaises(poller.CloneException):
            await self.poller.poll()

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @patch.object(poller.Poller, 'process_changes', AsyncMagicMock(
        spec=poller.Poller.process_changes))
    @async_test
    async def test_poll_clone_ok(self):
        self.poller.vcs.clone = AsyncMagicMock(spec=self.poller.vcs.clone)
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=False)
        self.poller.vcs.try_set_remote = AsyncMagicMock(
            spec=self.poller.vcs.try_set_remote)
        self.poller.vcs.update_submodule = AsyncMagicMock(
            spec=self.poller.vcs.update_submodule)

        r = await self.poller.poll()
        self.assertTrue(r)

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @patch.object(poller.Poller, 'process_changes', AsyncMagicMock(
        spec=poller.Poller.process_changes, side_effect=Exception))
    @async_test
    async def test_poll_process_changes_exception(self):
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=True)
        self.poller.vcs.try_set_remote = AsyncMagicMock(
            spec=self.poller.vcs.try_set_remote)
        self.poller.vcs.update_submodule = AsyncMagicMock(
            spec=self.poller.vcs.update_submodule)

        r = await self.poller.poll()
        self.assertFalse(r)
        self.assertEqual(len(self.poller.log.call_args_list), 3)

    @patch.object(poller.Poller, 'log', Mock(spec=poller.Poller.log))
    @patch.object(poller.Poller, 'process_changes', AsyncMagicMock(
        spec=poller.Poller.process_changes))
    @async_test
    async def test_poll_process_changes_ok(self):
        self.poller.vcs.workdir_exists = Mock(
            spec=self.poller.vcs.workdir_exists, return_value=True)
        self.poller.vcs.try_set_remote = AsyncMagicMock(
            spec=self.poller.vcs.try_set_remote)
        self.poller.vcs.update_submodule = AsyncMagicMock(
            spec=self.poller.vcs.update_submodule)

        r = await self.poller.poll()
        self.assertFalse(r)
        self.assertEqual(len(self.poller.log.call_args_list), 2)
