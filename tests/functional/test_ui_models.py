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
from toxicbuild.master.users import User as UserDBModel
from toxicbuild.ui.models import Slave, Repository, BuildSet, User
from tests import async_test


class BaseUITest(BaseFunctionalTest):

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
                                              'test-slave-add', 'localhost',
                                              123, '123', self.user)
            self.assertTrue(self.slave.id)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_get(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-get', 'localhost',
                                              123, '123', self.user)
            get_slave = yield from Slave.get(self.user,
                                             slave_name='test-slave-get')
            self.assertEqual(self.slave.id, get_slave.id)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_list(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-list', 'localhost',
                                              123, '123', self.user)
            slave_list = yield from Slave.list(self.user)
            self.assertEqual(len(slave_list), 1)
        finally:
            yield from self.slave.delete()

    @async_test
    def test_update(self):
        try:
            self.slave = yield from Slave.add(self.user,
                                              'test-slave-update', 'localhost',
                                              123, '123', self.user)
            yield from self.slave.update(host='192.168.0.1')
            get_slave = yield from Slave.get(self.user,
                                             slave_name='test-slave-update')
            self.assertEqual(self.slave.id, get_slave.id)
            self.assertEqual(get_slave.host, '192.168.0.1')
        finally:
            yield from self.slave.delete()


class RepositoryTest(BaseUITest):

    @async_test
    async def tearDown(self):
        if hasattr(self, 'repo'):
            await self.repo.delete()

        if hasattr(self, 'slave'):
            await self.slave.delete()

        await self.user.delete()

    @async_test
    def test_add(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 'localhost', 1234,
                                          '23', self.user)
        self.repo = yield from Repository.add(self.user, name='some-repo',
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
                                             repo_name='some-repo')
        self.assertEqual(self.repo.id, get_repo.id)

    @async_test
    def test_list(self):
        self.repo = yield from Repository.add(
            self.user, name='some-repo', url='bla@gla.com', owner=self.user,
            vcs_type='git',
            update_seconds=200)

        repo_list = yield from Repository.list(self.user)
        self.assertEqual(len(repo_list), 1)

    @async_test
    def test_update(self):
        self.repo = yield from Repository.add(
            self.user, name='some-repo', url='bla@gla.com', owner=self.user,
            vcs_type='git',
            update_seconds=200)
        yield from self.repo.update(update_seconds=100)
        get_repo = yield from Repository.get(self.user,
                                             repo_name=self.repo.name)
        self.assertEqual(self.repo.id, get_repo.id)
        self.assertEqual(get_repo.update_seconds, 100)

    @async_test
    def test_add_slave(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 'localhost', 1234,
                                          '123', self.user)
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.add_slave(self.slave)
        repo = yield from Repository.get(self.user, repo_name=self.repo.name)
        self.assertEqual(len(repo.slaves), 1)

    @async_test
    def test_remove_slave(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 'localhost', 1234,
                                          '2123', self.user)
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        yield from self.repo.remove_slave(self.slave)
        repo = yield from Repository.get(self.user, repo_name=self.repo.name)
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
        repo = yield from Repository.get(self.user, repo_name=self.repo.name)
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
        repo = yield from Repository.get(self.user, repo_name=self.repo.name)
        self.assertEqual(len(repo.branches), 0)

    @async_test
    def test_enable_plugin(self):
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.enable_plugin(
            'slack-notification',
            webhook_url='https://some.url.slack')
        repo = yield from Repository.get(self.user, repo_name='some-repo')
        self.assertEqual(len(repo.plugins), 1)

    @async_test
    def test_disable_plugin(self):
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200)
        yield from self.repo.enable_plugin(
            'slack-notification',
            webhook_url='https://some.url.slack')
        kw = {'name': 'slack-notification'}
        yield from self.repo.disable_plugin(**kw)
        repo = yield from Repository.get(self.user, repo_name='some-repo')
        self.assertEqual(len(repo.plugins), 0)


class BuildsetTest(BaseUITest):

    @async_test
    async def tearDown(self):
        if hasattr(self, 'repo'):
            await self.repo.delete()

        if hasattr(self, 'slave'):
            await  self.slave.delete()

        await self.user.delete()

    @async_test
    def test_list(self):
        self.slave = yield from Slave.add(self.user,
                                          'test-slave', 'localhost', 1234,
                                          '1234', self.user)
        self.repo = yield from Repository.add(self.user, name='some-repo',
                                              url='bla@gla.com',
                                              owner=self.user,
                                              vcs_type='git',
                                              update_seconds=200,
                                              slaves=[self.slave.name])
        buildsets = yield from BuildSet.list(self.user, repo_name='some-repo')
        self.assertEqual(len(buildsets), 0)


class UserTest(BaseFunctionalTest):

    @async_test
    async def setUp(self):
        self.requester = UserDBModel(email='asdf@asfd.com', is_superuser=True)
        self.requester.set_password('bla')
        await self.requester.save()

    @async_test
    async def tearDown(self):
        self.user.requester = self.requester
        await self.user.delete()
        await self.requester.delete()

    @async_test
    async def test_add(self):
        self.user = await User.add(
            self.requester, 'a@a.com', 'a', 'asdf', ['add_repo'])
        self.assertTrue(self.user.id)

    @async_test
    async def test_authenticate(self):
        self.user = await User.add(
            self.requester, 'a@a.com', 'a', 'asdf', ['add_repo'])
        auth = await User.authenticate('a@a.com', 'asdf')
        self.assertEqual(self.user.id, auth.id)
