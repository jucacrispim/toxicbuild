
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.master import document, users
from tests import async_test


class TestDoc(document.OwnedDocument):
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
        await users.Organization.drop_collection()

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
        with self.assertRaises(document.NotEnoughPerms):
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
        repos = await TestDoc.list_for_user(self.owner)
        count = await repos.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_list_for_user_no_perms(self):
        user = users.User(email='b@b.com', password='123')
        await user.save()
        repos = await TestDoc.list_for_user(user)
        count = await repos.count()
        self.assertEqual(count, 0)

    @async_test
    async def test_list_for_user_superuser(self):
        user = users.User(email='b@b.com', password='123', is_superuser=True)
        await user.save()
        repos = await TestDoc.list_for_user(user)
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
        repos = await TestDoc.list_for_user(user)
        count = await repos.count()
        self.assertEqual(count, 1)

    @async_test
    async def test_get_allowed_users_org_doc_owner(self):
        # user_a, the owner
        user_a = users.User(email='a@a.com')
        await user_a.save()
        org = users.Organization(name='my-org', owner=user_a)
        await org.save()
        # user_b, an allowed user
        user_b = users.User(email='b@b.com', member_of=[org])
        await user_b.save()
        # user_c, not allowed
        user_c = users.User(email='c@c.com')
        await user_c.save()

        repo = TestDoc(owner=org)
        await repo.save()
        allowed = await repo.get_allowed_users()
        allowed_users = await allowed.to_list()
        self.assertEqual(len(allowed_users), 2)

    @async_test
    async def test_get_allowed_users_user_doc_owner(self):
        # user_a, the owner
        user_a = users.User(email='a@a.com')
        await user_a.save()
        org = users.Organization(name='my-org', owner=user_a)
        await org.save()
        # user_b, an allowed user
        user_b = users.User(email='b@b.com', member_of=[org])
        await user_b.save()
        # user_c, not allowed
        user_c = users.User(email='c@c.com')
        await user_c.save()
        repo = TestDoc(owner=user_a)
        await repo.save()
        await user_a.reload()
        allowed = await repo.get_allowed_users()
        allowed_users = await allowed.to_list()
        self.assertEqual(len(allowed_users), 2)
