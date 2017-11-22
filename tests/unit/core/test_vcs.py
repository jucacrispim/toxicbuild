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
import os
from unittest import mock, TestCase
from toxicbuild.core import vcs, utils
from tests import async_test, AsyncMagicMock


@mock.patch.object(vcs, 'exec_cmd', mock.MagicMock())
class VCSTest(TestCase):

    def setUp(self):
        class DummyVcs(vcs.VCS):

            def checkout(self, name):
                pass

            def clone(self, name):
                pass

            def fetch(self):
                pass

            def pull(self, name):
                pass

            def has_changes(self):
                pass

            def get_revisions(self):
                pass

            def get_revisions_for_branch(self, branch, since={}):
                pass

            def get_remote_branches(self):
                pass

        super(VCSTest, self).setUp()
        self.vcs = DummyVcs('/some/workdir')

    @async_test
    def test_exec_cmd(self):
        yield from self.vcs.exec_cmd('ls')

        call_args = vcs.exec_cmd.call_args[0]
        self.assertEqual(call_args, ('ls', self.vcs.workdir))

    @async_test
    def test_workdir_exists(self):
        # sure this exists
        self.vcs.workdir = os.path.expanduser('~')

        self.assertTrue(self.vcs.workdir_exists())

        # now sure this not exists
        self.vcs.workdir = '/a-very-strange-dir-that-should-not-exist'
        self.assertFalse(self.vcs.workdir_exists())

    def test_get_vcs(self):
        # first with one that exists
        vcs_cls = vcs.get_vcs('git')

        self.assertEqual(vcs_cls, vcs.Git)

        # and one that will never exists (i hope)
        with self.assertRaises(vcs.VCSError):
            vcs.get_vcs('bla')

    def test_filter_remote_branches(self):
        remote_branches = ['master', 'release', 'dev-bla',
                           'other-branch', 'bla']
        filters = ['master', 'dev-*']
        expected = ['master', 'dev-bla']
        returned = self.vcs._filter_remote_branches(remote_branches, filters)
        self.assertEqual(returned, expected)


@mock.patch.object(vcs, 'exec_cmd', mock.MagicMock())
class GitTest(TestCase):

    def setUp(self):
        super(GitTest, self).setUp()
        self.vcs = vcs.Git('/some/workdir')

    @async_test
    def test_clone(self):
        url = 'git@somewhere.org/myproject.git'
        yield from self.vcs.clone(url)

        called_cmd = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(called_cmd, 'git clone %s %s --recursive' % (
            url, self.vcs.workdir))

    @async_test
    def test_fetch(self):
        expected_cmd = 'git fetch'

        @asyncio.coroutine
        def e(cmd, cwd):
            return cmd

        vcs.exec_cmd = e

        cmd = yield from self.vcs.fetch()
        self.assertEqual(cmd, expected_cmd)

    @async_test
    def test_checkout(self):
        expected_cmd = 'git checkout master'

        @asyncio.coroutine
        def e(cmd, cwd):
            assert cmd == expected_cmd

        vcs.exec_cmd = e

        yield from self.vcs.checkout('master')

    @async_test
    def test_pull(self):
        expected_cmd = 'git pull --no-edit origin master'

        @asyncio.coroutine
        def e(cmd, cwd):
            assert cmd == expected_cmd

        vcs.exec_cmd = e

        yield from self.vcs.pull('master')

    @async_test
    def test_has_changes(self):
        @asyncio.coroutine
        def e(cmd, cwd):
            return 'has changes!'

        vcs.exec_cmd = e

        has_changes = yield from self.vcs.has_changes()

        self.assertTrue(has_changes)

    @async_test
    def test_update_submodule(self):
        expected_cmd = ['git submodule init',
                        'git submodule update']
        self.COUNT = 0

        @asyncio.coroutine
        def e(cmd, cwd):
            assert cmd == expected_cmd[self.COUNT]
            self.COUNT += 1

        vcs.exec_cmd = e

        yield from self.vcs.update_submodule()

    @async_test
    def test_get_remote_branches(self):
        expected = 'git branch -r'

        emock = mock.Mock()

        @asyncio.coroutine
        def e(*a, **kw):
            emock(a[0])
            return 'origin/HEAD  -> origin/master\norigin/dev\norigin/master'

        fetch_mock = mock.Mock()

        @asyncio.coroutine
        def fetch():
            fetch_mock()

        expected_branches = ['dev', 'master']
        vcs.exec_cmd = e
        self.vcs.fetch = fetch
        self.vcs._update_remote_prune = AsyncMagicMock()
        branches = yield from self.vcs.get_remote_branches()
        called_cmd = emock.call_args[0][0]
        self.assertEqual(expected, called_cmd)
        self.assertEqual(expected_branches, branches)
        self.assertTrue(self.vcs._update_remote_prune.called)
        self.assertTrue(fetch_mock.called)

    @async_test
    def test_get_revisions_for_branch(self):
        now = utils.now()
        local = utils.utc2localtime(now)
        expected_cmd = '{} log --pretty=format:"%H | %ad | %an | %s" '.format(
            'git')
        expected_cmd += '--since="{}" --date=local'.format(
            datetime.datetime.strftime(local, self.vcs.date_format))

        @asyncio.coroutine
        def e(*a, **kw):
            assert a[0] == expected_cmd, a[0]
            log = '0sdflf093 | Thu Oct 20 16:30:23 2014 '
            log += '| zezinha do butiá | some good commit\n'
            log += '0sdflf095 | Thu Oct 20 16:20:23 2014 '
            log += '| seu fadu | Other good commit.\n'
            log += '09s80f9asdf | Thu Oct 20 16:10:23 2014 '
            log += '| capitão natário | I was the last consumed\n'
            return log

        vcs.exec_cmd = e
        revisions = yield from self.vcs.get_revisions_for_branch('master',
                                                                 since=now)
        # The first revision is the older one
        self.assertEqual(revisions[0]['author'], 'seu fadu')
        self.assertEqual(revisions[1]['commit'], '0sdflf093')

    @async_test
    def test_get_revisions_for_branch_without_since(self):
        expected_cmd = '{} log --pretty=format:"%H | %ad | %an | %s" {}'.\
                       format('git', '--date=local')

        @asyncio.coroutine
        def e(*a, **kw):
            assert a[0] == expected_cmd, a[0]
            log = '0sdflf093 | Thu Oct 20 16:30:23 2014 '
            log += '| zezinha do butiá | some good commit\n'
            log += '0sdflf095 | Thu Oct 20 16:20:23 2014 '
            log += '| seu fadu | Other good commit.\n'
            log += '09s80f9asdf | Thu Oct 20 16:10:23 2014 '
            log += '| capitão natário | I was the last consumed\n'
            return log

        vcs.exec_cmd = e
        revisions = yield from self.vcs.get_revisions_for_branch('master')
        self.assertEqual(revisions[0]['commit'], '0sdflf095')

    @async_test
    def test_get_revision(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        @asyncio.coroutine
        def remote_branches(*a, **kw):
            return ['origin/dev', 'origin/master']

        @asyncio.coroutine
        def branch_revisions(*a, **kw):
            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        revisions = yield from self.vcs.get_revisions(since=since)

        self.assertEqual(len(revisions['origin/master']), 2)
        self.assertEqual(len(revisions['origin/dev']), 2)

    @async_test
    def test_get_revision_with_branches(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        rb_mock = mock.Mock()

        @asyncio.coroutine
        def remote_branches(*a, **kw):
            rb_mock()
            return ['master', 'some-feature']

        @asyncio.coroutine
        def branch_revisions(*a, **kw):
            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        branches = ['master', 'some-feature']
        revisions = yield from self.vcs.get_revisions(since=since,
                                                      branches=branches)

        self.assertEqual(len(revisions['master']), 2)
        self.assertEqual(len(revisions['some-feature']), 2)
        self.assertTrue(rb_mock.called)

    @async_test
    def test_get_revisions_with_exception(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        rb_mock = mock.Mock()

        @asyncio.coroutine
        def remote_branches(*a, **kw):
            rb_mock()
            return ['master', 'some-feature']

        @asyncio.coroutine
        def branch_revisions(*a, **kw):
            if a[0] == 'some-feature':
                raise Exception

            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        branches = ['master', 'some-feature']
        revisions = yield from self.vcs.get_revisions(since=since,
                                                      branches=branches)

        self.assertEqual(len(revisions['master']), 2)
        self.assertFalse(revisions.get('some-feature'))

    @async_test
    def test_update_remote_prune(self):
        expected = 'git remote update --prune'
        yield from self.vcs._update_remote_prune()
        called = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)
