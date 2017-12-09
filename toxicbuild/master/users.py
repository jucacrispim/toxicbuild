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

from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, UUIDField, ListField,
                               ReferenceField, EmbeddedDocumentListField,
                               BooleanField, EmailField)
from mongomotor.queryset import PULL
from toxicbuild.core.utils import bcrypt_string
from toxicbuild.master import settings
from toxicbuild.master.exceptions import InvalidCredentials
from toxicbuild.master.utils import as_db_ref


class Organization(Document):
    uuid = UUIDField()

    name = StringField(required=True, unique=True)
    owner = ReferenceField('User', required=True)
    teams = EmbeddedDocumentListField('Team')

    async def add_user(self, user):
        """Adds a user to the organization"""

        await user.update(push__member_of=self)

    async def remove_user(self, user):
        """Removes a user from the organization."""

        await user.update(pull__member_of=self)

    @property
    def users(self):
        return User.objects.filter(member_of=self)

    async def save(self, *args, **kwargs):
        await super().save(*args, **kwargs)
        # we set it here so we can query for user's repo in a easier way
        owner = await self.owner
        # do not deref to avoid a query for all orgs
        organizations = [ref.id for ref in as_db_ref(owner, 'organizations')]
        if self.id not in organizations:
            await owner.update(push__organizations=self)


class User(Document):
    uuid = UUIDField()

    email = EmailField(required=True, unique=True)
    username = StringField(required=True, unique=True)
    password = StringField()
    is_superuser = BooleanField(default=False)
    # organizations owned by the user
    organizations = ListField(ReferenceField('Organization',
                                             reverse_delete_rule=PULL))
    # organizations which the user is part of, but not the owner
    member_of = ListField(ReferenceField('Organization'))
    # what the user can do: create_repo, create_slave or create_user
    allowed_actions = ListField(StringField())

    @classmethod
    async def authenticate(cls, username_or_email, password):
        """Authenticates an user. Returns an user if the user is
        authenticated. Raises ``InvalidCredentials`` if a user with
        this credentials does not exist.

        :param username_or_email: Username or email to use to authenticate.
        :param password: Not encrypted password."""

        salt = settings.BCRYPT_SALT
        password = bcrypt_string(password, salt)
        fields = ['username', 'email']
        for field in fields:
            kw = {field: username_or_email, 'password': password}
            try:
                user = await cls.objects.get(**kw)
                return user
            except cls.DoesNotExist:
                pass

        raise InvalidCredentials

    def to_dict(self):
        objdict = {'id': str(self.id),
                   'username': self.username,
                   'email': self.email}
        return objdict

    async def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email.split('@')[0]

        r = await super().save(*args, **kwargs)
        return r

    async def delete(self, *args, **kwargs):
        r = await super().delete(*args, **kwargs)
        await Organization.objects.filter(owner=self).delete()
        return r

    def set_password(self, password):
        salt = settings.BCRYPT_SALT
        self.password = bcrypt_string(password, salt)


class Team(EmbeddedDocument):
    uuid = UUIDField()

    name = StringField(required=True)
    members = ListField(ReferenceField(User))
