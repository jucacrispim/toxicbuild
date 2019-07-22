# -*- coding: utf-8 -*-

# Copyright 2018-2019 Juca Crispim <juca@poraodojuca.net>

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
import hashlib
import hmac
import jwt
from mongomotor.fields import StringField, DateTimeField, IntField
from toxicbuild.core import requests
from toxicbuild.core.utils import (string2datetime, now, localtime2utc,
                                   utc2localtime)
from toxicbuild.integrations import settings
from toxicbuild.integrations.base import (BaseIntegrationApp,
                                          BaseIntegrationInstallation)
from toxicbuild.integrations.exceptions import (BadRequestToExternalAPI,
                                                BadSignature)

__doc__ = """This module implements the integration with Github. It is
a `GithubApp <https://developer.github.com/apps/>`_  that reacts to events
sent by github webhooks and informs about build statuses using
`checks <https://developer.github.com/v3/checks/>`_.

Usage:
``````

.. code-block:: python

    # When a new installation is created on github we must create a
    # installation here.

    install = await GithubInstallation.create(github_install_id, user)

    # When a push happens or a pull request is created or synchronized
    # we update the code here.

    await install.update_repository(github_repo_id)

    # When a check is rerequested we request a build
    await install.repo_request_build(github_repo_id, branch, named_tree)

For information on how to setup the integration, see
:ref:`github-integration-config`"""


class GithubApp(BaseIntegrationApp):
    """A GitHub App. Only one app per ToxicBuild installation."""

    private_key = StringField(required=True)
    """The private key you generated in github."""

    app_id = IntField(required=True)
    """The id of the app in github."""

    jwt_expires = DateTimeField()
    """When auth token for the github api. expires. It must be in UTC"""

    jwt_token = StringField()
    """The auth token for the github api."""

    webhook_token = StringField()
    """The token used to sign the incomming request in the webhook. This must
    be set in the github app creation page."""

    @classmethod
    async def create_app(cls):
        with open(settings.GITHUB_PRIVATE_KEY) as fd:
            pk = fd.read()

        webhook_token = settings.GITHUB_WEBHOOK_TOKEN
        app = cls(private_key=pk, webhook_token=webhook_token)
        app.app_id = settings.GITHUB_APP_ID
        await app.save()
        return app

    def validate_token(self, signature, data):
        """Validates the incomming data in the webhook, sent by github."""

        sig = 'sha1=' + hmac.new(self.webhook_token.encode(), data,
                                 digestmod=hashlib.sha1).hexdigest()
        sig = sig.encode()
        if isinstance(signature, str):
            signature = signature.encode()

        eq = hmac.compare_digest(sig, signature)
        if not eq:
            raise BadSignature
        return True

    async def is_expired(self):
        """Informs if the jwt token is expired."""

        if self.jwt_expires and utc2localtime(self.jwt_expires) < now():
            return True
        return False

    async def get_jwt_token(self):
        """Returns the jwt token for authentication on the github api."""

        if self.jwt_token and not await self.is_expired():
            return self.jwt_token
        return await self.create_token()

    async def set_jwt_token(self, jwt_token):
        """Sets the jwt auth token."""

        self.jwt_token = jwt_token
        await self.save()

    async def set_expire_time(self, exp_time):
        """Sets the expire time for the jwt token"""
        self.jwt_expires = exp_time
        await self.save()

    def get_api_url(self):
        """Returns the url for the github app api."""

        return settings.GITHUB_API_URL + 'app'

    async def _create_jwt(self):
        exp_time = 10 * 59
        n = now()
        dt_expires = localtime2utc(n + timedelta(seconds=exp_time))
        ts_now = int(localtime2utc(n).timestamp())
        payload = {'iat': ts_now,
                   'exp': ts_now + exp_time,
                   'iss': self.app_id}

        self.log('creating jwt_token with payload {}'.format(payload),
                 level='debug')
        jwt_token = jwt.encode(payload, self.private_key, "RS256")
        await self.set_expire_time(dt_expires)
        await self.set_jwt_token(jwt_token.decode())
        return jwt_token.decode()

    async def create_token(self):
        """Creates a new token for the github api."""

        myjwt = await self._create_jwt()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}
        await requests.post(self.get_api_url(), headers=header)
        return myjwt

    @classmethod
    async def create_installation_token(cls, installation):
        """Creates a auth token for a given github installation

        :param installation: An instance of
          :class:`~toxicbuild.master.integrations.github.GitHubInstallation`
        """

        app = await cls.get_app()
        msg = 'Creating installation token for {}'.format(installation.id)
        app.log(msg, level='debug')

        myjwt = await app.get_jwt_token()
        header = {'Authorization': 'Bearer {}'.format(myjwt),
                  'Accept': 'application/vnd.github.machine-man-preview+json'}

        ret = await requests.post(installation.auth_token_url, headers=header)

        if ret.status != 201:
            raise BadRequestToExternalAPI(ret.status, ret.text)

        ret = ret.json()
        installation.auth_token = ret['token']
        expires_at = ret['expires_at'].replace('Z', '+0000')
        installation.expires = string2datetime(expires_at,
                                               dtformat="%Y-%m-%dT%H:%M:%S%z")
        await installation.save()
        return installation


GithubApp.ensure_indexes()


class GithubInstallation(BaseIntegrationInstallation):
    """An installation of the GitHub App. Installations have access to
    repositories and events."""

    app = GithubApp
    notif_name = 'github-check-run'

    # the id of the github app installation
    github_id = IntField()
    auth_token = StringField()
    expires = DateTimeField()

    @property
    def auth_token_url(self):
        """URL used to retrieve an access token for this installation."""

        url = settings.GITHUB_API_URL
        return url + 'installations/{}/access_tokens'.format(self.github_id)

    @property
    def token_is_expired(self):
        """Informs if the installation auth token is expired."""
        n = now()
        if n > utc2localtime(self.expires):
            return True
        return False

    async def get_header(
            self, accept='application/vnd.github.machine-man-preview+json'):

        if not self.auth_token or self.token_is_expired:
            await self.app.create_installation_token(self)

        header = {'Authorization': 'token {}'.format(self.auth_token),
                  'Accept': accept}
        return header

    async def _get_auth_url(self, url):
        """Returns the repo url with the acces token for authentication.

        :param url: The https repo url"""

        if not self.auth_token or self.token_is_expired:
            await self.app.create_installation_token(self)

        new_url = url.replace('https://', '')
        new_url = '{}x-access-token:{}@{}'.format('https://',
                                                  self.auth_token, new_url)
        return new_url

    async def list_repos(self):
        """Lists all respositories available to an installation.
        Returns a list of dictionaries with repositories' information"""

        header = await self.get_header()
        url = settings.GITHUB_API_URL + 'installation/repositories'
        ret = await requests.get(url, headers=header)
        if ret.status != 200:
            raise BadRequestToExternalAPI(ret.status, ret.text, url)
        ret = ret.json()
        return ret['repositories']

    async def get_repo(self, repo_full_name):
        """Get the repository (if available to the installation) from
        the github api.

        :param github_repo_id: The full name of the repository on github."""

        header = await self.get_header()
        url = settings.GITHUB_API_URL + 'repos/{}'.format(repo_full_name)
        ret = await requests.get(url, headers=header)
        if ret.status != 200:
            raise BadRequestToExternalAPI(ret.status, ret.text, url)
        return ret.json()


GithubInstallation.ensure_indexes()
