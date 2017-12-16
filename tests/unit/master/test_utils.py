# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from toxicbuild.master import utils, users
from tests import async_test


class UtilsTest(TestCase):

    def test_as_db_ref(self):
        user = users.User()
        self.assertFalse(utils.as_db_ref(user, 'member_of'))


class TestDoc(utils.OwnedDocument):
    pass


class OwnedDocuentTest(TestCase):

    @async_test
    async def setUp(self):
        self.owner = users.User(email='zezinho@nada.co', password='123')
        await self.owner.save()
        self.doc = TestDoc(owner=self.owner)
        await self.doc.save()

    @async_test
    async def tearDown(self):
        await TestDoc.drop_collection()
        await users.User.drop_collection()

    @async_test
    async def test_get_for_user_owner(self):
        doc = await TestDoc.get_for_user(
            self.owner, id=self.doc.id)
        self.assertEqual(doc, self.doc)

    @async_test
    async def test_get_for_user_superuser(self):
        user = users.User(email='b@b.com', password='123',
                          is_superuser=True)
        doc = await TestDoc.get_for_user(
            user, id=self.doc.id)
        self.assertEqual(doc, self.doc)

    @async_test
    async def test_get_for_user_denied(self):
        user = users.User(email='b@b.com', password='123')
        await user.save()
        with self.assertRaises(utils.NotEnoughPerms):
            await TestDoc.get_for_user(user, id=self.doc.id)

    @async_test
    async def test_get_for_user_organization(self):
        user = users.User(email='b@b.com', password='123')
        await user.save()
        org = users.Organization(name='my-org', owner=user)
        await org.save()
        repo = TestDoc(owner=org)
        await repo.save()
        await user.reload()
        returned = await TestDoc.get_for_user(user, id=repo.id)
        self.assertEqual(repo, returned)

    @async_test
    async def test_list_for_user(self):
        user = users.User(email='b@b.com', password='123')
        await user.save()
        org = users.Organization(name='my-org', owner=user)
        await org.save()
        repo = TestDoc(owner=org)
        await repo.save()
        repos = TestDoc.list_for_user(self.owner)
        count = await repos.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_list_for_user_no_perms(self):
        user = users.User(email='b@b.com', password='123')
        await user.save()
        repos = TestDoc.list_for_user(user)
        count = await repos.count()
        self.assertEqual(count, 0)

    @async_test
    async def test_list_for_user_superuser(self):
        user = users.User(email='b@b.com', password='123', is_superuser=True)
        await user.save()
        repos = TestDoc.list_for_user(user)
        count = await repos.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_list_for_user_organization(self):
        user = users.User(email='b@b.com', password='123')
        await user.save()
        org = users.Organization(name='my-org', owner=user)
        await org.save()
        repo = TestDoc(owner=org)
        await repo.save()
        await user.reload()
        repos = TestDoc.list_for_user(user)
        count = await repos.count()
        self.assertEqual(count, 1)
