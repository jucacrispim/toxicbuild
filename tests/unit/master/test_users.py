# -*- coding: utf-8 -*-

# Copyright 2017, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import patch, AsyncMock

import mongomotor

from toxicbuild.master import users
from tests import async_test


class OrganizationTest(TestCase):

    @async_test
    async def tearDown(self):
        await users.User.drop_collection()
        await users.Organization.drop_collection()

    @async_test
    async def test_add_user(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        user = users.User(email='outro@outro.com')
        await user.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.add_user(user)
        await user.reload()
        orgs = await user.member_of
        self.assertIn(org, orgs)

    @async_test
    async def test_remove_user(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        user = users.User(email='outro@outro.com')
        await user.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.add_user(user)
        await org.remove_user(user)
        await user.reload()
        orgs = await user.member_of
        self.assertNotIn(org, orgs)

    @async_test
    async def test_users(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        user = users.User(email='outro@outro.com')
        await user.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.add_user(user)

        users_list = await org.users.to_list()
        self.assertIn(user, users_list)

    @async_test
    async def test_save(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await owner.reload()
        orgs = await owner.organizations
        self.assertIn(org, orgs)

    @async_test
    async def test_save_org_already_in_list(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await owner.reload()
        await org.save()
        await owner.reload()
        orgs = await owner.organizations
        self.assertEqual(len(orgs), 1)

    @async_test
    async def test_delete(self):
        mongomotor.queryset.TEST_ENV = True
        owner = users.User(email='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.delete()
        await owner.reload()
        orgs = await owner.organizations
        self.assertFalse(orgs)

    @async_test
    async def test_set_password(self):
        user = users.User(email='a@a.com')
        user.set_password('asdf')
        await user.save()
        self.assertTrue(users.compare_bcrypt_string('asdf', user.password))


class UserTest(TestCase):

    @async_test
    async def tearDown(self):
        await users.User.drop_collection()
        await users.Organization.drop_collection()

    @async_test
    async def test_save_without_username(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        self.assertEqual(owner.username, 'ze')

    @async_test
    async def test_save(self):
        owner = users.User(email='ze@ze.com', username='mane')
        await owner.save()
        self.assertEqual(owner.username, 'mane')

    @async_test
    async def test_delete(self):
        owner = users.User(email='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await owner.delete()
        orgs = await users.Organization.objects.count()
        self.assertEqual(orgs, 0)

    @async_test
    async def test_authenticate_username(self):
        owner = users.User(email='ze@ze.com')
        owner.set_password('asdf')
        await owner.save()
        user = await users.User.authenticate('ze', 'asdf')
        self.assertEqual(user, owner)

    @async_test
    async def test_authenticate_email(self):
        owner = users.User(email='ze@ze.com')
        owner.set_password('asdf')
        await owner.save()
        user = await users.User.authenticate('ze@ze.com', 'asdf')
        self.assertEqual(user, owner)

    @async_test
    async def test_authenticate_invalid_credentials(self):
        owner = users.User(email='ze@ze.com')
        owner.set_password('asdf')
        await owner.save()
        with self.assertRaises(users.InvalidCredentials):
            await users.User.authenticate('ze@ze.com', 'asdfs')

    @async_test
    async def test_to_dict(self):
        owner = users.User(email='ze@ze.com')
        owner.set_password('asdf')
        await owner.save()
        expected = {'id': str(owner.id),
                    'username': owner.username,
                    'email': owner.email}
        returned = owner.to_dict()
        self.assertEqual(expected, returned)

    def test_user_name(self):
        user = users.User(username='bla')
        self.assertEqual(user.name, 'bla')


class ResetUserPasswordTokenTest(TestCase):

    @async_test
    async def tearDown(self):
        users.User.drop_collection()
        users.ResetUserPasswordToken.drop_collection()

    @async_test
    async def test_create(self):
        user = users.User(email='a@a.nada')
        await user.save()
        obj = await users.ResetUserPasswordToken.create(user)
        self.assertTrue(obj.id)

    @patch.object(users, 'send_email', AsyncMock(spec=users.send_email))
    @async_test
    async def test_send_reset_email(self):

        user = users.User(email='a@a.nada')
        await user.save()
        obj = await users.ResetUserPasswordToken.create(user)

        await obj.send_reset_email('he', 'ho {token}')

        self.assertFalse(obj.valid)
        self.assertTrue(users.send_email.called)
