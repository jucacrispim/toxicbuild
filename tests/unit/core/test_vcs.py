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
import os
import mock
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core import vcs


@mock.patch.object(vcs, 'exec_cmd', mock.MagicMock())
class VCSTest(AsyncTestCase):

    def setUp(self):
        super(VCSTest, self).setUp()
        self.vcs = vcs.VCS('/some/workdir')

    @gen_test
    def test_exec_cmd(self):
        yield from self.vcs.exec_cmd('ls')

        call_args = vcs.exec_cmd.call_args[0]
        self.assertEqual(call_args, ('ls', self.vcs.workdir))

    @gen_test
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


@mock.patch.object(vcs, 'exec_cmd', mock.MagicMock())
class GitTest(AsyncTestCase):

    def setUp(self):
        super(GitTest, self).setUp()
        self.vcs = vcs.Git('/some/workdir')

    @gen_test
    def test_clone(self):
        url = 'git@somewhere.org/myproject.git'
        yield from self.vcs.clone(url)

        called_cmd = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(called_cmd, 'git clone %s %s' % (url,
                                                          self.vcs.workdir))

    @gen_test
    def test_fetch(self):
        expected_cmd = 'git fetch 2>&1'

        @asyncio.coroutine
        def e(cmd, cwd):
            return cmd

        vcs.exec_cmd = e

        cmd = yield from self.vcs.fetch()
        self.assertEqual(cmd, expected_cmd)

    @gen_test
    def test_checkout(self):
        expected_cmd = 'git checkout master'

        @asyncio.coroutine
        def e(cmd, cwd):
            assert cmd == expected_cmd

        vcs.exec_cmd = e

        yield from self.vcs.checkout('master')

    @gen_test
    def test_pull(self):
        expected_cmd = 'git pull --no-edit origin master'

        @asyncio.coroutine
        def e(cmd, cwd):
            assert cmd == expected_cmd

        vcs.exec_cmd = e

        yield from self.vcs.pull('origin/master')

    @gen_test
    def test_has_changes(self):
        @asyncio.coroutine
        def e(cmd, cwd):
            return 'has changes!'

        vcs.exec_cmd = e

        has_changes = yield from self.vcs.has_changes()

        self.assertTrue(has_changes)

    @gen_test
    def test_get_remote_branches(self):
        expected = 'git branch -r'

        emock = mock.Mock()

        @asyncio.coroutine
        def e(*a, **kw):
            emock(a[0])
            return 'origin/HEAD  -> origin/master\norigin/dev\norigin/master'

        expected_branches = ['origin/dev', 'origin/master']
        vcs.exec_cmd = e
        branches = yield from self.vcs.get_remote_branches()
        called_cmd = emock.call_args[0][0]
        self.assertEqual(expected, called_cmd)
        self.assertEqual(expected_branches, branches)

    @gen_test
    def test_get_revisions_for_branch(self):
        now = datetime.datetime.now()
        expected_cmd = '{} log --pretty=format:"%H | %ad" '.format('git')
        expected_cmd += '--since="{}"'.format(
            datetime.datetime.strftime(now, self.vcs.date_format))

        @asyncio.coroutine
        def e(*a, **kw):
            assert a[0] == expected_cmd, a[0]
            log = '0sdflf093 | Thu Oct 20 16:30:23 2014 -0200\n'
            log += '0sdflf095 | Thu Oct 20 16:20:23 2014 -0200\n'
            return log

        vcs.exec_cmd = e
        revisions = yield from self.vcs.get_revisions_for_branch('master',
                                                                 since=now)
        self.assertEqual(revisions[0]['commit'], '0sdflf095')

    @gen_test
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
