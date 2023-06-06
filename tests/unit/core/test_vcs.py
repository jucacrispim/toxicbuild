# -*- coding: utf-8 -*-

# Copyright 2015 2016, 2018, 2023 Juca Crispim <juca@poraodojuca.net>

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
import os
from unittest import mock, TestCase
from toxicbuild.core import vcs, utils
from tests import async_test


@mock.patch.object(vcs, 'exec_cmd', mock.AsyncMock())
class VCSTest(TestCase):

    def setUp(self):
        class DummyVcs(vcs.VCS):

            def checkout(self, name):
                pass

            def clone(self, name):
                pass

            def set_remote(self, url, remote_name):
                pass

            def get_remote(self):
                pass

            def try_set_remote(self, url, remote_name):
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

            def create_local_branch(self, branch_name, base_name):
                pass

            def delete_local_branch(self, branch_name):
                pass

            def add_remote(self, remote_url, remote_name):
                pass

            def import_external_branch(self, external_url, external_name,
                                       external_branch, into):
                pass

            def get_local_revisions(self, since, branches):
                pass

        super(VCSTest, self).setUp()
        self.vcs = DummyVcs('/some/workdir')

    @async_test
    async def test_exec_cmd(self):
        await self.vcs.exec_cmd('ls')

        call_args = vcs.exec_cmd.call_args[0]
        self.assertEqual(call_args, ('ls', self.vcs.workdir))

    @async_test
    async def test_workdir_exists(self):
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


@mock.patch.object(vcs, 'exec_cmd', mock.AsyncMock())
class GitTest(TestCase):

    def setUp(self):
        super(GitTest, self).setUp()
        self.vcs = vcs.Git('/some/workdir')

    @async_test
    async def test_set_remote_origin_config(self):
        await self.vcs._set_remote_origin_config()
        called_cmd = vcs.exec_cmd.call_args[0][0]
        self.assertTrue(called_cmd.startswith('git config remote.origin'))

    @async_test
    async def test_clone(self):
        url = 'git@somewhere.org/myproject.git'
        self.vcs._set_remote_origin_config = mock.AsyncMock()
        await self.vcs.clone(url)

        called_cmd = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(
            called_cmd,
            'git clone --depth=2 %s %s --recursive' % (url, self.vcs.workdir))

    @async_test
    async def test_set_remote(self):
        url = 'git@otherplace.com/myproject.git'
        await self.vcs.set_remote(url)
        called_cmd = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(called_cmd, 'git remote set-url origin {}'.format(
            url))

    @async_test
    async def test_get_remote(self):
        expected = "git remote -v | grep -m1 origin | "
        expected += "sed -e 's/origin\s*//g' -e 's/(.*)//g'"
        await self.vcs.get_remote()
        called_cmd = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(called_cmd, expected)

    @async_test
    async def test_add_remote(self):
        expected = 'git remote add new-origin http://someurl.net/bla.git'
        self.vcs.exec_cmd = mock.AsyncMock(spec=self.vcs.exec_cmd)
        await self.vcs.add_remote('http://someurl.net/bla.git', 'new-origin')
        called = self.vcs.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @async_test
    async def test_rm_remote(self):
        expected = 'git remote rm new-origin'
        self.vcs.exec_cmd = mock.AsyncMock(spec=self.vcs.exec_cmd)
        await self.vcs.rm_remote('new-origin')
        called = self.vcs.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)

    @mock.patch.object(vcs.Git, 'get_remote', mock.AsyncMock(
        spec=vcs.Git.get_remote, return_value='git@bla.com/bla.git'))
    @mock.patch.object(vcs.Git, 'set_remote', mock.AsyncMock(
        spec=vcs.Git.set_remote))
    @async_test
    async def test_try_set_remote_same_url(self):
        url = 'git@bla.com/bla.git'
        await self.vcs.try_set_remote(url)
        self.assertFalse(self.vcs.set_remote.called)

    @mock.patch.object(vcs.Git, 'get_remote', mock.AsyncMock(
        spec=vcs.Git.get_remote, return_value='git@bla.com/bla.git'))
    @mock.patch.object(vcs.Git, 'set_remote', mock.AsyncMock(
        spec=vcs.Git.set_remote))
    @async_test
    async def test_try_set_remote_other_url(self):
        url = 'git@bla.com/other.git'
        await self.vcs.try_set_remote(url)
        self.assertTrue(self.vcs.set_remote.called)

    @async_test
    async def test_fetch(self):
        expected_cmd = 'git fetch'

        async def e(cmd, cwd):
            return cmd

        vcs.exec_cmd = e

        cmd = await self.vcs.fetch()
        self.assertEqual(cmd, expected_cmd)

    @async_test
    async def test_create_local_branch(self):
        expected_cmd = 'git branch new-branch'

        async def e(cmd, cwd):
            return cmd

        vcs.exec_cmd = e

        self.vcs.checkout = mock.AsyncMock(spec=self.vcs.checkout)
        cmd = await self.vcs.create_local_branch('new-branch', 'master')
        self.assertEqual(cmd, expected_cmd)
        self.assertTrue(self.vcs.checkout.called)

    @async_test
    async def test_delete_local_branch(self):
        expected_cmd = 'git branch -D new-branch'

        async def e(cmd, cwd):
            return cmd

        vcs.exec_cmd = e

        self.vcs.checkout = mock.AsyncMock(spec=self.vcs.checkout)
        cmd = await self.vcs.delete_local_branch('new-branch')
        self.assertEqual(cmd, expected_cmd)
        self.assertTrue(self.vcs.checkout.called)

    @async_test
    async def test_checkout(self):
        expected_cmd = 'git checkout master'

        async def e(cmd, cwd):
            assert cmd == expected_cmd

        vcs.exec_cmd = e

        await self.vcs.checkout('master')

    @async_test
    async def test_pull(self):
        expected_cmd = 'git pull --no-edit origin master'

        async def e(cmd, cwd):
            assert cmd == expected_cmd

        vcs.exec_cmd = e

        await self.vcs.pull('master')

    @async_test
    async def test_branch_exists(self):
        self.vcs.exec_cmd = mock.AsyncMock(spec=self.vcs.exec_cmd)
        r = await self.vcs.branch_exists('some-branch')
        self.assertTrue(r)

    @async_test
    async def test_branch_exists_doenst_exist(self):
        self.vcs.exec_cmd = mock.AsyncMock(spec=self.vcs.exec_cmd,
                                           side_effect=vcs.ExecCmdError)
        r = await self.vcs.branch_exists('some-branch')
        self.assertFalse(r)

    @async_test
    async def test_import_external_branch(self):
        external_url = 'http://other-place.net/bla.git'
        external_name = 'other-repo'
        external_branch = 'master'
        into = 'other-repo:master'
        self.vcs.branch_exists = mock.AsyncMock(spec=self.vcs.branch_exists,
                                                return_value=True)
        self.vcs.add_remote = mock.AsyncMock(spec=self.vcs.add_remote)
        self.vcs.rm_remote = mock.AsyncMock(spec=self.vcs.rm_remote)
        self.vcs.checkout = mock.AsyncMock(spec=self.vcs.checkout)
        self.vcs.pull = mock.AsyncMock(spec=self.vcs.pull)
        await self.vcs.import_external_branch(external_url, external_name,
                                              external_branch, into)
        remote_added = self.vcs.add_remote.call_args[0]
        remote_expected = (external_url, external_name)
        checkout = self.vcs.checkout.call_args[0][0]
        checkout_expected = 'other-repo:master'
        pull = self.vcs.pull.call_args[0]
        pull_expected = (external_branch, external_name)
        rm = self.vcs.rm_remote.call_args[0]
        rm_expected = 'other-repo'
        self.assertEqual(remote_added, remote_expected)
        self.assertEqual(checkout, checkout_expected)
        self.assertEqual(pull, pull_expected)
        self.assertEqual(rm, (rm_expected,))

    @async_test
    async def test_import_external_branch_dont_exist(self):
        external_url = 'http://other-place.net/bla.git'
        external_name = 'other-repo'
        external_branch = 'master'
        into = 'other-repo:master'
        self.vcs.branch_exists = mock.AsyncMock(spec=self.vcs.branch_exists,
                                                return_value=False)
        self.vcs.create_local_branch = mock.AsyncMock(
            spec=self.vcs.create_local_branch)
        self.vcs.add_remote = mock.AsyncMock(spec=self.vcs.add_remote)
        self.vcs.checkout = mock.AsyncMock(spec=self.vcs.checkout)
        self.vcs.pull = mock.AsyncMock(spec=self.vcs.pull)
        await self.vcs.import_external_branch(external_url, external_name,
                                              external_branch, into)

        branch_created = self.vcs.create_local_branch.call_args[0]
        branch_expected = (into, 'master')
        remote_added = self.vcs.add_remote.call_args[0]
        remote_expected = (external_url, external_name)
        checkout = self.vcs.checkout.call_args[0][0]
        checkout_expected = 'other-repo:master'
        pull = self.vcs.pull.call_args[0]
        pull_expected = (external_branch, external_name)

        self.assertEqual(branch_created, branch_expected)
        self.assertEqual(remote_added, remote_expected)
        self.assertEqual(checkout, checkout_expected)
        self.assertEqual(pull, pull_expected)

    @async_test
    async def test_has_changes(self):
        async def e(cmd, cwd):
            return 'has changes!'

        vcs.exec_cmd = e

        has_changes = await self.vcs.has_changes()

        self.assertTrue(has_changes)

    @async_test
    async def test_update_submodule(self):
        expected_cmd = ['git submodule init',
                        'git submodule update']
        self.COUNT = 0

        async def e(cmd, cwd):
            assert cmd == expected_cmd[self.COUNT]
            self.COUNT += 1

        vcs.exec_cmd = e

        await self.vcs.update_submodule()

    @async_test
    async def test_get_remote_branches(self):
        expected = 'git branch -r'

        emock = mock.Mock()

        async def e(*a, **kw):
            emock(a[0])
            r = 'origin/HEAD  -> origin/master\norigin/dev\norigin/master'
            r += '\norigin/a/bad/one'
            return r

        fetch_mock = mock.Mock()

        async def fetch():
            fetch_mock()

        expected_branches = set(['dev', 'master', 'a/bad/one'])
        vcs.exec_cmd = e
        self.vcs.fetch = fetch
        self.vcs._update_remote_prune = mock.AsyncMock()
        branches = await self.vcs.get_remote_branches()
        called_cmd = emock.call_args[0][0]
        self.assertEqual(expected, called_cmd)
        self.assertEqual(expected_branches, branches)
        self.assertTrue(self.vcs._update_remote_prune.called)
        self.assertTrue(fetch_mock.called)

    @async_test
    async def test_get_remote_branches_no_head(self):
        expected = 'git branch -r'

        emock = mock.Mock()

        async def e(*a, **kw):
            emock(a[0])
            r = 'origin/master'
            return r

        fetch_mock = mock.Mock()

        async def fetch():
            fetch_mock()

        expected_branches = set(['master'])
        vcs.exec_cmd = e
        self.vcs.fetch = fetch
        self.vcs._update_remote_prune = mock.AsyncMock()
        branches = await self.vcs.get_remote_branches()
        called_cmd = emock.call_args[0][0]
        self.assertEqual(expected, called_cmd)
        self.assertEqual(expected_branches, branches)
        self.assertTrue(self.vcs._update_remote_prune.called)
        self.assertTrue(fetch_mock.called)

    @async_test
    async def test_get_revisions_for_branch(self):
        now = utils.now()
        local = utils.utc2localtime(now)

        commit_fmt = "%H | %ad | %an | %s | %+b {}".format(
            self.vcs._commit_separator)

        expected_cmd = '{} log --pretty=format:"{}" '.\
                       format('git', commit_fmt)

        expected_cmd += '--since="{}" --date=local'.format(
            datetime.datetime.strftime(local, self.vcs.date_format))

        body = '\n\nObrigado deus dos maronitas.\nFadul Abdala\n'
        body += 'O Grão-turco das putas.'

        async def e(*a, **kw):
            assert a[0] == expected_cmd, a[0]
            log = '0sdflf093 | Thu Oct 20 16:30:23 2014 '
            log += '| zezinha do butiá | some good commit | <end-toxiccommit>'
            log += '\n0sdflf095 | Thu Oct 20 16:20:23 2014 '
            log += '| seu fadu | Other good commit. | '
            log += body + '<end-toxiccommit>\n'
            log += '09s80f9asdf | Thu Oct 20 16:10:23 2014 '
            log += '| capitão natário | I was the last consumed\n | '
            log += '<end-toxiccommit>\n'
            return log

        vcs.exec_cmd = e
        revisions = await self.vcs.get_revisions_for_branch('master',
                                                            since=now)
        # The first revision is the older one
        self.assertEqual(revisions[0]['author'], 'seu fadu')
        self.assertEqual(revisions[0]['body'], body)
        self.assertEqual(revisions[1]['commit'], '0sdflf093')

    @async_test
    async def test_get_revisions_for_branch_without_since(self):
        commit_fmt = "%H | %ad | %an | %s | %+b {}".format(
            self.vcs._commit_separator)

        expected_cmd = '{} log --pretty=format:"{}" {}'.\
                       format('git', commit_fmt, '--date=local')

        body = '\n\nObrigado deus dos maronitas.\nFadul Abdala\n'
        body += 'O Grão-turco das putas.'

        async def e(*a, **kw):
            assert a[0] == expected_cmd, a[0]
            log = '0sdflf093 | Thu Oct 20 16:30:23 2014 '
            log += '| zezinha do butiá | some good commit | <end-toxiccommit>'
            log += '\n0sdflf095 | Thu Oct 20 16:20:23 2014 '
            log += '| seu fadu | Other good commit. | '
            log += body + '<end-toxiccommit>\n'
            log += '09s80f9asdf | Thu Oct 20 16:10:23 2014 '
            log += '| capitão natário | I was the last consumed\n | '
            log += '<end-toxiccommit>\n'
            return log

        vcs.exec_cmd = e
        revisions = await self.vcs.get_revisions_for_branch('master')
        self.assertEqual(revisions[0]['commit'], '0sdflf095')

    @async_test
    async def test_get_local_revisions(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        async def branch_revisions(*a, **kw):
            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_revisions_for_branch = branch_revisions

        revisions = await self.vcs.get_local_revisions(since=since,
                                                       branches=['a-branch'])

        self.assertEqual(len(revisions['a-branch']), 2)

    @async_test
    async def test_get_local_revisions_no_revs(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        async def branch_revisions(*a, **kw):
            return []

        self.vcs.get_revisions_for_branch = branch_revisions

        revisions = await self.vcs.get_local_revisions(since=since,
                                                       branches=['a-branch'])

        self.assertNotIn('a-branch', revisions)

    @mock.patch.object(vcs.LoggerMixin, 'log', mock.Mock())
    @async_test
    async def test_get_local_revisions_error(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        async def branch_revisions(*a, **kw):
            raise Exception

        self.vcs.get_revisions_for_branch = branch_revisions

        revisions = await self.vcs.get_local_revisions(since=since,
                                                       branches=['a-branch'])

        self.assertNotIn('a-branch', revisions)

    @async_test
    async def test_get_revision(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        async def remote_branches(*a, **kw):
            return ['origin/dev', 'origin/master']

        async def branch_revisions(*a, **kw):
            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        revisions = await self.vcs.get_revisions(since=since)

        self.assertEqual(len(revisions['origin/master']), 2)
        self.assertEqual(len(revisions['origin/dev']), 2)

    @async_test
    async def test_get_revision_no_revs_for_branch(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        async def remote_branches(*a, **kw):
            return ['origin/dev', 'origin/master']

        branch_revisions = mock.AsyncMock(
            side_effect=[[{'123adsf': now}, {'asdf123': now}], []]
        )

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        revisions = await self.vcs.get_revisions(since=since)

        self.assertNotIn('origin/master', revisions)
        self.assertEqual(len(revisions['origin/dev']), 2)

    @async_test
    async def test_get_revision_with_branches(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        rb_mock = mock.Mock()

        async def remote_branches(*a, **kw):
            rb_mock()
            return ['master', 'some-feature']

        async def branch_revisions(*a, **kw):
            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        branches = ['master', 'some-feature']
        revisions = await self.vcs.get_revisions(since=since,
                                                 branches=branches)

        self.assertEqual(len(revisions['master']), 2)
        self.assertEqual(len(revisions['some-feature']), 2)
        self.assertTrue(rb_mock.called)

    @async_test
    async def test_get_revisions_with_exception(self):
        now = datetime.datetime.now()
        since = {'master': now,
                 'dev': now}

        rb_mock = mock.Mock()

        async def remote_branches(*a, **kw):
            rb_mock()
            return ['master', 'some-feature']

        async def branch_revisions(*a, **kw):
            if a[0] == 'some-feature':
                raise Exception

            return [{'123adsf': now}, {'asdf123': now}]

        self.vcs.get_remote_branches = remote_branches
        self.vcs.get_revisions_for_branch = branch_revisions

        branches = ['master', 'some-feature']
        revisions = await self.vcs.get_revisions(since=since,
                                                 branches=branches)

        self.assertEqual(len(revisions['master']), 2)
        self.assertFalse(revisions.get('some-feature'))

    @async_test
    async def test_update_remote_prune(self):
        expected = 'git remote update --prune'
        await self.vcs._update_remote_prune()
        called = vcs.exec_cmd.call_args[0][0]
        self.assertEqual(expected, called)
