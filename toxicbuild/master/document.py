# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

from mongoengine.queryset import Q
from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import GenericReferenceField, StringField
from toxicbuild.master.exceptions import NotEnoughPerms
from toxicbuild.master.users import User


class OwnedDocument(Document):
    """An abstract document for objects that have an owner. Subclass it
    to use it.

    Example:
    ´´´´´´´´

    class MyOwnedDocument(OwnedDocument):

       some_field = StringField()
    """

    owner = GenericReferenceField(required=True)
    """The user or organization who owns the document"""

    name = StringField(required=True)
    """The name of the document."""

    full_name = StringField(required=True, unique=True)
    """Full name of the document in the form `owner-name/doc-name`"""

    meta = {'abstract': True}

    async def save(self, *args, **kwargs):
        if not self.full_name:
            owner = await self.owner
            self.full_name = '{}/{}'.format(owner.name, self.name)
        r = await super().save(*args, **kwargs)
        return r

    @classmethod
    async def get_for_user(cls, user, **kwargs):
        """Returns a repository if ``user`` has permission for it.
        If not raises an error.

        :param user: User who is requesting the repository.
        :param kwargs: kwargs to match the repository.
        """
        obj = await cls.objects.get(**kwargs)
        has_perms = await obj.check_perms(user)
        if not has_perms:
            msg = 'The user {} has no permissions for this object'.format(
                user.id)
            raise NotEnoughPerms(msg)
        return obj

    @classmethod
    async def list_for_user(cls, user, **kwargs):
        """Returns a queryset of repositories in which the user has read
        permission"""
        member_of = await user.member_of
        member_of = [ref.id for ref in member_of]
        organizations = await user.organizations
        organizations = [ref.id for ref in organizations]

        if user.is_superuser:
            qs = cls.objects
        else:
            qs = cls.objects(
                Q(owner=user) |
                Q(__raw__={'owner._ref.$id': {'$in': organizations}}) |
                Q(__raw__={'owner._ref.$id': {'$in': member_of}}))

        return qs.no_cache().filter(**kwargs)

    async def _get_member_of_organizations(self, owner):
        """Returns a list with the ids of the organizations that a owner.
        is member of and a list of ids of organizations the owner of the
        document owns.
        """

        if hasattr(owner, 'member_of'):
            member_of = await owner.member_of
            member_of = [ref.id for ref in member_of]
        else:
            member_of = [owner.id]

        if hasattr(owner, 'organizations'):
            organizations = await owner.organizations
            organizations = [ref.id for ref in organizations]
        else:
            organizations = [owner.id]

        return member_of, organizations

    async def get_allowed_users(self):
        """Returns a queryset of users that have read permission."""

        owner = await self.owner
        member_of, organizations = await self._get_member_of_organizations(
            owner)

        qs = User.objects(Q(id=owner.id) |
                          Q(organizations__in=organizations) |
                          Q(member_of__in=member_of + organizations))

        return qs

    async def check_perms(self, user):
        if user.is_superuser:
            return True

        owner = await self.owner
        owner_id = owner.id

        member_of, organizations = await self._get_member_of_organizations(
            owner)

        if owner == user or owner_id in member_of or \
           owner_id in organizations:
            has_perms = True
        else:
            has_perms = False

        return has_perms


class ExternalRevisionIinfo(EmbeddedDocument):
    """Information about code that came from an external source.
    Shared by :class:`~toxicbuild.master.repository.RepositoryRevision` and
    :class:`~toxicbuild.master.build.Build`"""

    url = StringField(required=True)
    """The url of the external repo"""

    name = StringField(required=True)
    """A name to indentify the external repo."""

    branch = StringField(required=True)
    """The name of the branch in the external repo."""

    into = StringField(required=True)
    """A name for a local branch to clone the external branch into."""

    def to_dict(self):
        """Returns a dict representations of the object"""
        return {'url': self.url,
                'name': self.name,
                'branch': self.branch,
                'into': self.into}
