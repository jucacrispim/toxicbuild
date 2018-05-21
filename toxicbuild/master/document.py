# -*- coding: utf-8 -*-

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

from bson.dbref import DBRef
from mongoengine.queryset import Q
from mongomotor import Document
from mongomotor.fields import GenericReferenceField
from toxicbuild.master.exceptions import NotEnoughPerms
from toxicbuild.master.users import User
from toxicbuild.master.utils import as_db_ref


class OwnedDocument(Document):

    owner = GenericReferenceField(required=True)

    meta = {'abstract': True}

    @classmethod
    async def get_for_user(cls, user, **kwargs):
        """Returns a repository if ``user`` has permission for it.
        If not raises an error.

        :param user: User who is requesting the repository.
        :param kwargs: kwargs to match the repository.
        """
        obj = await cls.objects.get(**kwargs)
        has_perms = await obj._check_perms(user)
        if not has_perms:
            msg = 'The user {} has no permissions for this object'.format(
                user.id)
            raise NotEnoughPerms(msg)
        return obj

    @classmethod
    def list_for_user(cls, user, **kwargs):
        """Returns a queryset of repositories in which the user has read
        permission"""
        member_of = [ref.id for ref in as_db_ref(user, 'member_of')]
        organizations = [ref.id for ref in as_db_ref(user, 'organizations')]

        if user.is_superuser:
            qs = cls.objects
        else:
            qs = cls.objects(
                Q(owner=user) |
                Q(__raw__={'owner._ref.$id': {'$in': organizations}}) |
                Q(__raw__={'owner._ref.$id': {'$in': member_of}}))

        return qs.filter(**kwargs)

    def get_allowed_users(self):
        """Returns a queryset of users that have read permission."""

        owner = as_db_ref(self, 'owner')
        try:
            member_of = [ref.id for ref in as_db_ref(owner, 'member_of')]
            organizations = [ref.id for ref in as_db_ref(
                owner, 'organizations')]
        except (KeyError, UnboundLocalError):
            member_of = [owner.id]
            organizations = [owner.id]

        qs = User.objects(Q(id=owner.id) |
                          Q(organizations__in=organizations) |
                          Q(member_of__in=member_of + organizations))

        return qs

    async def _check_perms(self, user):
        if user.is_superuser:
            return True

        owner = await self.owner
        owner_id = DBRef(owner.__class__.__name__.lower(), owner.id)
        member_of = as_db_ref(user, 'member_of')
        organizations = as_db_ref(user, 'organizations')
        if owner == user or owner_id in member_of or \
           owner_id in organizations:
            has_perms = True
        else:
            has_perms = False

        return has_perms
