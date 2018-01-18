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

import time
import jwt
from mongomotor import Document
from mongomotor.fields import (StringField, DateTimeField, IntField,
                               ReferenceField)
from toxicbuild.core import requests
from toxicbuild.core.utils import string2datetime, now
from toxicbuild.master import settings
from toxicbuild.master.users import User
from toxicbuild.master.integrations.exceptions import AppDoesNotExist


class GithubApp(Document):
    """A GitHub App. Only one app per ToxicBuild installation. You cannot
    have two different GitHub apps for the same ToxicBuild instance."""

    private_key = settings.GITHUB_PRIVATE_KEY
    app_id = IntField(unique=True)

    @classmethod
    async def _create_jwt(cls):
        app = await cls.objects.first()
        now = int(time.time())
        payload = {'iat': now,
                   'exp': now + (10 * 60),
                   'iss': app.app_id}
        with open(cls.private_key) as fd:
            pk = fd.read()

        return jwt.encode(payload, pk, "RS256")

    @classmethod
    async def app_exists(cls):
        """Checks if an app already exists in the system."""

        count = await cls.objects.count()
        return bool(count)

    @classmethod
    async def create_installation_token(cls, installation):
        """Creates a auth token for a given github installation

        :param installation: An instance of
        :class:`~toxicbuild.master.integrations.github.GitHubInstallation`"""

        if not await cls.app_exists():
            raise AppDoesNotExist

        myjwt = await cls._create_jwt()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}

        ret = await requests.post(installation.auth_token_url, header=header)
        ret = ret.json()
        installation.auth_token = ret['token']
        installation.expires = string2datetime(ret['expires_at'],
                                               dtformat="%Y-%m-%dT%H:%M:%SZ")
        await installation.save()
        return installation


class GithubInstallation(Document):
    """An installation of the GitHub App. Installations have access to
    repositories and events."""

    app = GithubApp

    user = ReferenceField(User)
    github_id = IntField()
    auth_token = StringField()
    expires = DateTimeField()

    @property
    def auth_token_url(self):
        """URL used to retrieve an access token for this installation."""

        return 'https://api.github.com/installations/{}/access_tokens'.format(
            self.id)

    @property
    def token_is_expired(self):
        n = now()
        if n > self.expires:
            return True
        return False

    async def _get_header(self):
        if not self.auth_token or self.token_is_expired:
            await self.app.create_installation_token(self)

        header = {'Authorization': 'token {}'.format(self.auth_token),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}
        return header

    async def list_repos(self):
        """Lists all respositories available to an installation.
        Returns a list of dictionaries with repositories' information"""

        header = await self._get_header()
        url = 'https://api.github.com/installation/repositories'
        ret = await requests.post(url, header=header)
        ret = ret.json()
        return ret['repositories']
