# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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

from datetime import timedelta
import secrets

from mongomotor import Document, EmbeddedDocument
from mongomotor.fields import (StringField, UUIDField, ListField,
                               ReferenceField, EmbeddedDocumentListField,
                               BooleanField, EmailField, DateTimeField)
from mongomotor.queryset import PULL

from toxicbuild.core.utils import (bcrypt_string, compare_bcrypt_string,
                                   now, localtime2utc)
from toxicbuild.master.exceptions import InvalidCredentials
from toxicbuild.master.utils import send_email


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
        organizations = await owner.organizations
        organizations = [ref.id for ref in organizations]
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
    # what the user can do: add_repo, add_slave or add_user
    allowed_actions = ListField(StringField())

    @classmethod
    async def authenticate(cls, username_or_email, password):
        """Authenticates an user. Returns an user if the user is
        authenticated. Raises ``InvalidCredentials`` if a user with
        this credentials does not exist.

        :param username_or_email: Username or email to use to authenticate.
        :param password: Not encrypted password."""

        fields = ['username', 'email']
        for field in fields:
            kw = {field: username_or_email}
            try:
                user = await cls.objects.get(**kw)
                if compare_bcrypt_string(password, user.password):
                    return user
            except cls.DoesNotExist:
                pass

        raise InvalidCredentials

    @property
    def name(self):
        return self.username

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
        self.password = bcrypt_string(password)


class ResetUserPasswordToken(Document):

    TOKEN_LEN = 64

    user = ReferenceField(User, required=True)
    email = StringField(required=True)
    token = StringField(required=True)
    expires = DateTimeField(required=True)
    valid = BooleanField(default=True)

    @classmethod
    async def create(cls, user):
        """Creates a new reset token for a given user.

        :param user: An instance of :class:`~toxicbuild.master.users.User`
        """

        token = secrets.token_urlsafe(cls.TOKEN_LEN)
        expires = localtime2utc(now()) + timedelta(days=1)
        obj = cls(user=user, token=token, expires=expires, email=user.email)
        await obj.save()
        return obj

    async def send_reset_email(self, subject, msg):
        """Sends an email with information on how to reset a password.

        :param recipient: The recipient email address.
        :param subject: The subject of the e-mail.
        :param msg: The body of the email. If you have a {token} field
          in the body, the expire token will be included. It usually is
          is inserted in the reset url."""

        body = msg.format(token=self.token)

        await send_email([self.email], subject, body)
        self.valid = False
        await self.save()


class Team(EmbeddedDocument):
    uuid = UUIDField()

    name = StringField(required=True)
    members = ListField(ReferenceField(User))
