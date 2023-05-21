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
from toxicbuild.common.interfaces import (SlaveInterface,
                                          RepositoryInterface,
                                          BuildSetInterface,
                                          UserInterface,
                                          BaseInterface)
from toxicbuild.master.repository import Repository as RepoDBModel
from toxicbuild.master.users import User as UserDBModel
from toxicbuild.ui import settings
from tests import async_test
from tests.functional import BaseFunctionalTest, start_all, stop_all


def setUpModule():
    BaseInterface.settings = settings
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
    async def test_add(self):
        try:
            self.slave = await SlaveInterface.add(self.user,
                                                  'test-slave-add',
                                                  123, '123', self.user,
                                                  host='localhost')
            self.assertTrue(self.slave.id)
        finally:
            await self.slave.delete()

    @async_test
    async def test_get(self):
        try:
            self.slave = await SlaveInterface.add(self.user,
                                                  'test-slave-get',
                                                  123, '123', self.user,
                                                  host='localhost')
            get_slave = await SlaveInterface.get(
                self.user, slave_name_or_id='asdf/test-slave-get')
            self.assertEqual(self.slave.id, get_slave.id)
        finally:
            await self.slave.delete()

    @async_test
    async def test_list(self):
        try:
            self.slave = await SlaveInterface.add(self.user,
                                                  'test-slave-list',
                                                  123, '123', self.user,
                                                  host='localhost')
            slave_list = await SlaveInterface.list(self.user)
            self.assertEqual(len(slave_list), 1, slave_list)
        finally:
            await self.slave.delete()

    @async_test
    async def test_update(self):
        try:
            self.slave = await SlaveInterface.add(self.user,
                                                  'test-slave-update',
                                                  123, '123', self.user,
                                                  host='localhost')
            await self.slave.update(host='192.168.0.1')
            get_slave = await SlaveInterface.get(
                self.user, slave_name_or_id='asdf/test-slave-update')
            self.assertEqual(self.slave.id, get_slave.id)
            self.assertEqual(get_slave.host, '192.168.0.1')
        finally:
            await self.slave.delete()


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
    async def test_add(self):
        self.slave = await SlaveInterface.add(self.user,
                                              'test-slave', 1234,
                                              '23', self.user,
                                              host='localhost')
        self.repo = await RepositoryInterface.add(
            self.user, name='asdf/some-repo',
            url='bla@gla.com',
            owner=self.user,
            vcs_type='git',
            update_seconds=200,
            slaves=[self.slave.name])
        self.assertTrue(self.repo.id)

    @async_test
    async def test_get(self):
        self.repo = await RepositoryInterface.add(
            self.user, name='some-repo', url='bla@gla.com',
            owner=self.user, vcs_type='git',
            update_seconds=200)
        get_repo = await RepositoryInterface.get(self.user,
                                                 name='asdf/some-repo')
        self.assertEqual(self.repo.id, get_repo.id)

    @async_test
    async def test_list(self):
        self.repo = await RepositoryInterface.add(
            self.user, name='some-repo', url='bla@gla.com', owner=self.user,
            vcs_type='git',
            update_seconds=200)

        repo_list = await RepositoryInterface.list(self.user)
        self.assertEqual(len(repo_list), 1, repo_list)

    @async_test
    async def test_update(self):
        self.repo = await RepositoryInterface.add(
            self.user, name='some-repo', url='bla@gla.com', owner=self.user,
            vcs_type='git',
            update_seconds=200)
        await self.repo.update(update_seconds=100)
        get_repo = await RepositoryInterface.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(self.repo.id, get_repo.id)
        self.assertEqual(get_repo.update_seconds, 100)

    @async_test
    async def test_add_slave(self):
        self.slave = await SlaveInterface.add(
            self.user,
            'test-slave', 1234,
            '123', self.user, host='localhost')

        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200)
        await self.repo.add_slave(self.slave)
        repo = await RepositoryInterface.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.slaves), 1)

    @async_test
    async def test_remove_slave(self):
        self.slave = await SlaveInterface.add(self.user,
                                              'test-slave', 1234,
                                              '2123', self.user,
                                              host='localhost')
        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200,
                                                  slaves=[self.slave.name]
                                                  )
        await self.repo.remove_slave(self.slave)
        repo = await RepositoryInterface.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.slaves), 0)

    @async_test
    async def test_add_branch(self):
        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200)
        await self.repo.add_branch('master', True)
        repo = await RepositoryInterface.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.branches), 1)

    @async_test
    async def test_remove_branch(self):
        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200)
        await self.repo.add_branch('master', True)
        await self.repo.remove_branch('master')
        repo = await RepositoryInterface.get(
            self.user, name='asdf/' + self.repo.name)
        self.assertEqual(len(repo.branches), 0)

    @async_test
    async def test_add_or_update_secret(self):
        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200)
        await self.repo.add_or_update_secret('something', 'very secret')
        secrets = await self.repo.get_secrets()
        self.assertEqual(secrets['something'], 'very secret')

    @async_test
    async def test_rm_secret(self):
        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200)
        await self.repo.add_or_update_secret('something', 'very secret')
        await self.repo.rm_secret('something')
        secrets = await self.repo.get_secrets()
        self.assertNotIn('something', secrets)

    @async_test
    async def test_replace_secrets(self):
        self.repo = await RepositoryInterface.add(self.user,
                                                  name='some-repo',
                                                  url='bla@gla.com',
                                                  owner=self.user,
                                                  vcs_type='git',
                                                  update_seconds=200)
        await self.repo.add_or_update_secret('something', 'very secret')
        new = {'something': 'super secret', 'other': 'also secret'}
        await self.repo.replace_secrets(**new)
        secrets = await self.repo.get_secrets()
        self.assertEqual(secrets['something'], 'super secret')
        self.assertEqual(secrets['other'], 'also secret')


class BuildsetTest(BaseUITest):

    @async_test
    async def tearDown(self):
        if hasattr(self, 'repo'):
            await self.repo.delete()

        if hasattr(self, 'slave'):
            await self.slave.delete()

        await self.user.delete()

    @async_test
    async def test_list(self):
        self.slave = await SlaveInterface.add(self.user,
                                              'test-slave', 1234,
                                              '1234', self.user,
                                              host='localhost')
        self.repo = await RepositoryInterface.add(
            self.user, name='some-repo',
            url='bla@gla.com',
            owner=self.user,
            vcs_type='git',
            update_seconds=200,
            slaves=[self.slave.name])

        buildsets = await BuildSetInterface.list(
            self.user, repo_name_or_id='asdf/' + 'some-repo')
        self.assertEqual(len(buildsets), 0)


class UserTest(BaseFunctionalTest):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.root = UserDBModel(id=settings.ROOT_USER_ID, email='bla@bla.nada',
                               is_superuser=True)
        await cls.root.save(force_insert=True)

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await cls.root.delete()

    @async_test
    async def tearDown(self):
        await self.user.delete()

    @async_test
    async def test_add(self):
        self.user = await UserInterface.add('a@a.com', 'a', 'asdf',
                                            ['add_repo'])
        self.assertTrue(self.user.id)

    @async_test
    async def test_authenticate(self):
        self.user = await UserInterface.add('a@a.com', 'a', 'asdf',
                                            ['add_repo'])
        auth = await UserInterface.authenticate('a@a.com', 'asdf')
        self.assertEqual(self.user.id, auth.id)

    @async_test
    async def test_get(self):
        self.user = await UserInterface.add('a@a.com', 'a', 'asdf',
                                            ['add_repo'])
        u = await UserInterface.get(email='a@a.com')

        self.assertEqual(u.id, self.user.id)
