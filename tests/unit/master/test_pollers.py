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
import mock
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.master import pollers, repositories


class GitPollerTest(AsyncTestCase):
    @mock.patch.object(pollers, 'get_vcs', mock.MagicMock())
    def setUp(self):
        super(GitPollerTest, self).setUp()
        self.repo = repositories.Repository(
            url='git@somewhere.org/project.git')

        self.poller = pollers.Poller(
            self.repo, vcs_type='git', workdir='workdir',
            notify_only_latest=True)

    def tearDown(self):
        repositories.RepositoryRevision.drop_collection()
        repositories.Repository.drop_collection()
        super(GitPollerTest, self).tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def test_notify_changes(self):
        self.CALLED = False

        def recv(sender, revision=None):
            self.CALLED = True

        pollers.revision_added.connect(recv)
        self.poller.notify_change(mock.MagicMock())

        self.assertTrue(self.CALLED)

    @gen_test
    def test_process_changes(self):
        now = datetime.datetime.now()
        self.CALLED = 0

        def recv(*a, **kw):
            self.CALLED += 1

        pollers.revision_added.connect(recv)

        yield from self._create_db_revisions()

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now},
                               {'commit': 'asdf213', 'commit_date': now}]}

        self.poller.vcs.get_revisions = gr
        yield from self.poller.process_changes()

        # call only 1 because self.poller.notify_only_latest is True
        self.assertEqual(self.CALLED, 1)

    @gen_test
    def test_poll(self):
        yield from self._create_db_revisions()

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
            return {'master': [{'commit': '123sdf', 'commit_date': now},
                               {'commit': 'asdf213', 'commit_date': now}]}

        self.poller.vcs.get_revisions = gr
        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.vcs.clone = clone
        self.poller.vcs.has_changes = has_changes

        yield from self.poller.poll()

        self.assertTrue(self.CLONE_CALLED)

    @asyncio.coroutine
    def _create_db_revisions(self):
        yield self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()

        for r in range(2):
            rev = repositories.RepositoryRevision(
                repository=rep, commit='123asdf', branch='master',
                commit_date=now)

            yield rev.save()
