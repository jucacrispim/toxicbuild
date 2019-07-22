# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from toxicbuild.master.repository import Repository as RepoDBModel
from toxicbuild.master.users import User as UserDBModel
from toxicbuild.ui import settings
from toxicbuild.ui.models import Slave, Repository, BuildSet, User
from tests import async_test
from tests.functional import BaseFunctionalTest, start_all, stop_all


def setUpModule():
    start_all()


def tearDownModule():
    stop_all()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(RepoDBModel.drop_collection())


class BaseUITest(BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    @async_test
    async def setUp(self):
        self.user = UserDBModel(email='asdf@asfd.com', is_superuser=True)
        self.user.set_password('bla')
        await self.user.save()

    @async_test
    async def tearDown(self):
        await self.user.delete()


class SlaveTest(BaseUITest):

    @async_test
    def test_add(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-add',
                                              123, '123', self.user,
                                              host='localhost')
            self.assertTrue(self.slave.id)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_get(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-get',
                                              123, '123', self.user,
                                              host='localhost')
            get_slave = yield from Slave.get(
                self.user, slave_name_or_id='asdf/test-slave-get')
            self.assertEqual(self.slave.id, get_slave.id)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_list(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-list',
                                              123, '123', self.user,
                                              host='localhost')
            slave_list = yield from Slave.list(self.user)
            self.assertEqual(len(slave_list), 1, slave_list)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_update(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-update',
                                              123, '123', self.user,
                                              host='localhost')
            yield from self.slave.update(host='192.168.0.1')
            get_slave = yield from Slave.get(
                self.user, slave_name_or_id='asdf/test-slave-update')
            self.assertEqual(self.slave.id, get_slave.id)
            self.assertEqual(get_slave.host, '192.168.0.1')
        finally:
            yield from self.slave.delete()


class RepositoryTest(BaseUITest):

    @classmethod
    @async_test
    async def setUpClass(cls):
        super().setUpClass()
        await RepoDBModel.drop_collection()

    @async_test
    async def tearDown(self):
        if hasattr(self, 'repo'):
            await self.repo.delete()

        if hasattr(self, 'slave'):
            await self.slave.delete()

        await self.user.delete()
        await RepoDBModel.drop_collection()

    @async_test
    def test_add(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 1234,
                                          '23', self.user,
                                          host='localhost')
        self.repo = yield from Repository.add(self.user, name='asdf/some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        self.assertTrue(self.repo.id)

    @async_test
    def test_get(self):
        self.repo = yield from Repository.add(
            self.user, name='some-repo', url='bla@gla.com',
            owner=self.user, vcs_type='git',
            update_seconds=200)
        get_repo = yield from Repository.get(self.user,
                                             name='asdf/some-repo')
        self.assertEqual(self.repo.id, get_repo.id)

    @async_test
    def test_list(self):
        self.repo = yield from Repository.add(
            self.user, name='some-repo', url='bla@gla.com', owner=self.user,
            vcs_type='git',
            update_seconds=200)

        repo_list = yield from Repository.list(self.user)
        self.assertEqual(len(repo_list), 1, repo_list)

    @async_test
    def test_update(self):
        self.repo = yield from Repository.add(
            self.user, name='some-repo', url='bla@gla.com', owner=self.user,
            vcs_type='git',
            update_seconds=200)
        yield from self.repo.update(update_seconds=100)
        get_repo = yield from Repository.get(self.user,
                                             name='asdf/' + self.repo.name)
        self.assertEqual(self.repo.id, get_repo.id)
        self.assertEqual(get_repo.update_seconds, 100)

    @async_test
    def test_add_slave(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 1234,
                                          '123', self.user, host='localhost')
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_slave(self.slave)
        repo = yield from Repository.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.slaves), 1)

    @async_test
    def test_remove_slave(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 1234,
                                          '2123', self.user, host='localhost')
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        yield from self.repo.remove_slave(self.slave)
        repo = yield from Repository.get(self.user,
                                         name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.slaves), 0)

    @async_test
    def test_add_branch(self):
        self.repo = yield from Repository.add(self.user,
                                              name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_branch('master', True)
        repo = yield from Repository.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.branches), 1)

    @async_test
    def test_remove_branch(self):
        self.repo = yield from Repository.add(self.user,
                                              name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_branch('master', True)
        yield from self.repo.remove_branch('master')
        repo = yield from Repository.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.branches), 0)


class BuildsetTest(BaseUITest):

    @async_test
    async def tearDown(self):
        if hasattr(self, 'repo'):
            await self.repo.delete()

        if hasattr(self, 'slave'):
            await self.slave.delete()

        await self.user.delete()

    @async_test
    def test_list(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 1234,
                                          '1234', self.user, host='localhost')
        self.repo = yield from Repository.add(
            self.user, name='some-repo',
            url='bla@gla.com',
            owner=self.user,
            vcs_type='git',
            update_seconds=200,
            slaves=[self.slave.name])

        buildsets = yield from BuildSet.list(
            self.user, repo_name_or_id='asdf/' + 'some-repo')
        self.assertEqual(len(buildsets), 0)


class UserTest(BaseFunctionalTest):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.root = UserDBModel(id=settings.ROOT_USER_ID, email='bla@bla.nada',
                               is_superuser=True)
        await cls.root.save()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await cls.root.delete()

    @async_test
    async def tearDown(self):
        await self.user.delete()

    @async_test
    async def test_add(self):
        self.user = await User.add('a@a.com', 'a', 'asdf', ['add_repo'])
        self.assertTrue(self.user.id)

    @async_test
    async def test_authenticate(self):
        self.user = await User.add('a@a.com', 'a', 'asdf', ['add_repo'])
        auth = await User.authenticate('a@a.com', 'asdf')
        self.assertEqual(self.user.id, auth.id)
