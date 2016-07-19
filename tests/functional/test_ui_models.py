# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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


from tests.functional import BaseFunctionalTest
from tornado.testing import gen_test
from toxicbuild.master.scheduler import scheduler
from toxicbuild.ui.models import Slave, Repository, BuildSet

scheduler.stop()


class SlaveTest(BaseFunctionalTest):

    @gen_test
    def tearDown(self):
        slave = yield from Slave.get(slave_name='test-slave')
        yield from slave.delete()

        super().tearDown()

    @gen_test
    def test_add(self):
        slave = yield from Slave.add('test-slave', '192.168.0.1', 1234)
        self.assertTrue(slave.id)

    @gen_test
    def test_get(self):
        slave = yield from Slave.add('test-slave', '192.168.0.1', 1234)
        get_slave = yield from Slave.get(slave_name='test-slave')
        self.assertEqual(slave.id, get_slave.id)

    @gen_test
    def test_list(self):
        yield from Slave.add('test-slave', '192.168.0.1', 1234)
        slave_list = yield from Slave.list()
        self.assertEqual(len(slave_list), 1)


class RepositoryTest(BaseFunctionalTest):

    @gen_test
    def tearDown(self):
        if hasattr(self, 'repo'):
            yield from self.repo.delete()

        if hasattr(self, 'slave'):
            yield from self.slave.delete()

        super().tearDown()

    @gen_test
    def test_add(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234)
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        self.assertTrue(self.repo.id)

    @gen_test
    def test_get(self):
        self.repo = yield from Repository.add(
            name='some-repo', url='bla@gla.com', vcs_type='git',
            update_seconds=200)
        get_repo = yield from Repository.get(repo_name='some-repo')
        self.assertEqual(self.repo.id, get_repo.id)

    @gen_test
    def test_list(self):
        self.repo = yield from Repository.add(
            name='some-repo', url='bla@gla.com', vcs_type='git',
            update_seconds=200)

        repo_list = yield from Repository.list()
        self.assertEqual(len(repo_list), 1)

    @gen_test
    def test_add_slave(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234)
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_slave(self.slave)
        repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(len(repo.slaves), 1)

    @gen_test
    def test_remove_slave(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234)
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        yield from self.repo.remove_slave(self.slave)
        repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(len(repo.slaves), 0)


class BuildsetTest(BaseFunctionalTest):

    @gen_test
    def tearDown(self):
        if hasattr(self, 'repo'):
            yield from self.repo.delete()

        if hasattr(self, 'slave'):
            yield from self.slave.delete()

    @gen_test
    def test_list(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234)
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        buildsets = yield from BuildSet.list(repo_name='some-repo')
        self.assertEqual(len(buildsets), 0)
