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


import asyncio
from tests.functional import BaseFunctionalTest
from toxicbuild.ui.models import Slave, Repository, BuildSet
from tests import async_test


class SlaveTest(BaseFunctionalTest):

    @async_test
    def test_add(self):
        try:
            self.slave = yield from Slave.add('test-slave-add', 'localhost',
                                              123, '123')
            self.assertTrue(self.slave.id)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_get(self):
        try:
            self.slave = yield from Slave.add('test-slave-get', 'localhost',
                                              123, '123')
            get_slave = yield from Slave.get(slave_name='test-slave-get')
            self.assertEqual(self.slave.id, get_slave.id)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_list(self):
        try:
            self.slave = yield from Slave.add('test-slave-list', 'localhost',
                                              123, '123')
            slave_list = yield from Slave.list()
            self.assertEqual(len(slave_list), 1)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_update(self):
        try:
            self.slave = yield from Slave.add('test-slave-update', 'localhost',
                                              123, '123')
            yield from self.slave.update(host='192.168.0.1')
            get_slave = yield from Slave.get(slave_name='test-slave-update')
            self.assertEqual(self.slave.id, get_slave.id)
            self.assertEqual(get_slave.host, '192.168.0.1')
        finally:
            yield from self.slave.delete()


class RepositoryTest(BaseFunctionalTest):

    def tearDown(self):
        loop = asyncio.get_event_loop()

        if hasattr(self, 'repo'):
            loop.run_until_complete(self.repo.delete())

        if hasattr(self, 'slave'):
            loop.run_until_complete(self.slave.delete())

        super().tearDown()

    @async_test
    def test_add(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234,
                                          '23')
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        self.assertTrue(self.repo.id)

    @async_test
    def test_get(self):
        self.repo = yield from Repository.add(
            name='some-repo', url='bla@gla.com', vcs_type='git',
            update_seconds=200)
        get_repo = yield from Repository.get(repo_name='some-repo')
        self.assertEqual(self.repo.id, get_repo.id)

    @async_test
    def test_list(self):
        self.repo = yield from Repository.add(
            name='some-repo', url='bla@gla.com', vcs_type='git',
            update_seconds=200)

        repo_list = yield from Repository.list()
        self.assertEqual(len(repo_list), 1)

    @async_test
    def test_update(self):
        self.repo = yield from Repository.add(
            name='some-repo', url='bla@gla.com', vcs_type='git',
            update_seconds=200)
        yield from self.repo.update(update_seconds=100)
        get_repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(self.repo.id, get_repo.id)
        self.assertEqual(get_repo.update_seconds, 100)

    @async_test
    def test_add_slave(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234,
                                          '123')
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_slave(self.slave)
        repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(len(repo.slaves), 1)

    @async_test
    def test_remove_slave(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234,
                                          '2123')
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        yield from self.repo.remove_slave(self.slave)
        repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(len(repo.slaves), 0)

    @async_test
    def test_add_branch(self):
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_branch('master', True)
        repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(len(repo.branches), 1)

    @async_test
    def test_remove_branch(self):
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_branch('master', True)
        yield from self.repo.remove_branch('master')
        repo = yield from Repository.get(repo_name=self.repo.name)
        self.assertEqual(len(repo.branches), 0)


class BuildsetTest(BaseFunctionalTest):

    @async_test
    def tearDown(self):
        if hasattr(self, 'repo'):
            yield from self.repo.delete()

        if hasattr(self, 'slave'):
            yield from self.slave.delete()

    @async_test
    def test_list(self):
        self.slave = yield from Slave.add('test-slave', 'localhost', 1234,
                                          '1234')
        self.repo = yield from Repository.add(name='some-repo',
                                              url='bla@gla.com',
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        buildsets = yield from BuildSet.list(repo_name='some-repo')
        self.assertEqual(len(buildsets), 0)
