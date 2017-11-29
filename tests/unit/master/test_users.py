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

import time
from unittest import TestCase
from toxicbuild.master import users
from tests import async_test


class OrganizationTest(TestCase):

    @async_test
    async def tearDown(self):
        await users.User.drop_collection()
        await users.Organization.drop_collection()

    @async_test
    async def test_add_user(self):
        owner = users.User(username='ze@ze.com')
        await owner.save()
        user = users.User(username='outro@outro.com')
        await user.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.add_user(user)
        await user.reload()
        orgs = await user.member_of
        self.assertIn(org, orgs)

    @async_test
    async def test_users(self):
        owner = users.User(username='ze@ze.com')
        await owner.save()
        user = users.User(username='outro@outro.com')
        await user.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.add_user(user)

        users_list = await org.users.to_list()
        self.assertIn(user, users_list)

    @async_test
    async def test_save(self):
        owner = users.User(username='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await owner.reload()
        orgs = await owner.organizations
        self.assertIn(org, orgs)

    @async_test
    async def test_delete(self):
        owner = users.User(username='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await org.delete()
        time.sleep(1)
        await owner.reload()
        orgs = await owner.organizations
        self.assertFalse(orgs)


class UserTest(TestCase):

    @async_test
    async def tearDown(self):
        await users.User.drop_collection()
        await users.Organization.drop_collection()

    @async_test
    async def test_delete(self):
        owner = users.User(username='ze@ze.com')
        await owner.save()
        org = users.Organization(name='org', owner=owner)
        await org.save()
        await owner.delete()
        orgs = await users.Organization.objects.count()
        self.assertEqual(orgs, 0)
