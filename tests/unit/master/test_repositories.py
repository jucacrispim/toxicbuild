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
from unittest.mock import Mock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.master import repositories, build


class RepositoryTest(AsyncTestCase):

    def setUp(self):
        super(RepositoryTest, self).setUp()
        self.repo = repositories.Repository(
            url="git@somewhere.com/project.git", vcs_type='git',
            update_seconds=100)

    def tearDown(self):
        repositories.Repository.drop_collection()
        repositories.RepositoryRevision.drop_collection()
        build.Slave.drop_collection()
        super(RepositoryTest, self).tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    def test_workdir(self):
        expected = 'src/gitsomewhere.com-project.git'
        self.assertEqual(self.repo.workdir, expected)

    def test_poller(self):
        self.assertEqual(type(self.repo.poller), repositories.Poller)

    @gen_test
    def test_create(self):
        slave = yield from build.Slave.create('bla.com', 1234)
        repo = yield from repositories.Repository.create(
            'git@somewhere.com', 300, 'git', slaves=[slave])

        self.assertTrue(repo.id)
        self.assertEqual(repo.slaves[0], slave)

    @gen_test
    def test_get(self):
        slave = yield from build.Slave.create('bla.com', 1234)
        old_repo = yield from repositories.Repository.create(
            'git@somewhere.com', 300, 'git', slaves=[slave])
        new_repo = yield from repositories.Repository.get(url=old_repo.url)

        self.assertEqual(old_repo, new_repo)
        self.assertEqual(new_repo.slaves[0], slave)

    @patch.object(repositories.utils, 'log', Mock())
    @patch.object(repositories, 'scheduler', Mock(
        spec=repositories.scheduler))
    def test_schedule(self):
        self.repo.schedule()

        self.assertTrue(repositories.scheduler.add.called)

    @patch.object(repositories.utils, 'log', Mock())
    @patch.object(repositories, 'scheduler', Mock(
        spec=repositories.scheduler))
    @gen_test
    def test_schedule_all(self):
        yield from self._create_db_revisions()
        yield from self.repo.schedule_all()

        self.assertTrue(repositories.scheduler.add.called)

    @gen_test
    def test_first_run(self):
        yield from self._create_db_revisions()

        mpoll = Mock()

        @asyncio.coroutine
        def poll():
            mpoll()

        self.repo.poller.poll = poll
        self.repo.schedule = Mock()

        self.repo.first_run()

        for task in asyncio.Task.all_tasks():
            yield from task

        self.assertTrue(self.repo.schedule.called)

    @gen_test
    def test_add_slave(self):
        yield from self._create_db_revisions()
        slave = yield from repositories.Slave.create(host='127.0.0.1',
                                                     port=7777)
        yield from self.repo.add_slave(slave)

        self.assertEqual(len(self.repo.slaves), 1)

    @gen_test
    def test_remove_slave(self):
        yield from self._create_db_revisions()
        slave = yield from repositories.Slave.create(host='127.0.0.1',
                                                     port=7777)
        yield from self.repo.add_slave(slave)
        yield from self.repo.remove_slave(slave)

        self.assertEqual(len(self.repo.slaves), 0)

    @gen_test
    def test_get_latest_revision_for_branch(self):
        yield from self._create_db_revisions()
        expected = '123asdf1'
        rev = yield from self.repo.get_latest_revision_for_branch('master')
        self.assertEqual(expected, rev.commit)

    @gen_test
    def test_get_latest_revisions(self):
        yield from self._create_db_revisions()
        revs = yield from self.repo.get_latest_revisions()

        self.assertEqual(revs['master'].commit, '123asdf1')
        self.assertEqual(revs['dev'].commit, '123asdf1')

    @gen_test
    def test_add_revision(self):
        yield self.repo.save()
        branch = 'master'
        commit = 'asdf213'
        commit_date = datetime.datetime.now()
        rev = yield from self.repo.add_revision(branch, commit, commit_date)
        self.assertTrue(rev.id)

    @asyncio.coroutine
    def _create_db_revisions(self):
        yield self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()

        for r in range(2):
            for branch in ['master', 'dev']:
                rev = repositories.RepositoryRevision(
                    repository=rep, commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    commit_date=now + datetime.timedelta(r))

                yield rev.save()
