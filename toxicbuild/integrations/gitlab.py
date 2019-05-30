# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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


from mongomotor.fields import StringField, IntField
from toxicbuild.core import requests
from toxicbuild.integrations import settings
from toxicbuild.integrations.base import BaseIntegrationInstallation
from toxicbuild.integrations.exceptions import BadRequestToExternalAPI

__doc__ = """This module implements integration with gitlab. Imports
Repositories from GitLab and reacts to messages sent by gitlab to
toxicbuild's integrations webhook.
See: `GitLab integration docs <https://about.gitlab.com/partners/integrate/>`_.
"""


class GitLabInstallation(BaseIntegrationInstallation):

    code = StringField(requied=True)
    """The code first sent by the gitlab api. Used to generate the access token
    """

    access_token = StringField()
    """Access token for the gitlab api"""

    gitlab_user_id = IntField()
    """The user's id at gitlab."""

    REDIRECT_URI = settings.INTEGRATIONS_HTTP_URL + 'gitlab/setup'

    async def _get_header(self):
        if not self.access_token:
            await self.create_access_token()

        headers = {'Authorization': 'Bearer {}'.format(self.access_token)}
        return headers

    async def get_user_id(self):
        """Gets the user id from the gitlab api.
        """
        header = await self._get_header()
        url = settings.GITLAB_API_URL + 'user'
        r = await requests.get(url, headers=header)
        if r.status != 200:
            raise BadRequestToExternalAPI(r.status, r.text)

        r = r.json()
        self.gitlab_user_id = r['id']
        await self.save()

    async def create_access_token(self):
        """Creates an access token to the gitlab api.
        """
        url = settings.GITLAB_URL + 'oauth/token'

        params = {'client_id': settings.GITLAB_APP_ID,
                  'client_secret': settings.GITLAB_APP_SECRET,
                  'code': self.code,
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.REDIRECT_URI}

        r = await requests.post(url, params=params)
        if r.status != 200:
            raise BadRequestToExternalAPI(r.status, r.text)

        r = r.json()
        self.access_token = r['access_token']
        # don't save here 'cause the doc is saved by get_user_id()
        # await self.save()
        await self.get_user_id()

    async def _get_auth_url(self, url):
        """Returns the repo url with the acces token for authentication.

        :param url: The https repo url"""

        if not self.access_token:
            await self.create_access_token()

        new_url = url.replace('https://', '')
        new_url = '{}gitlab.com:{}@{}'.format('https://',
                                              self.access_token, new_url)
        return new_url

    async def list_repos(self):
        """Lists the repositories using GitLab API.
        """

        header = await self._get_header()
        url = settings.GITLAB_API_URL + 'users/{}/projects'.format(
            self.gitlab_user_id)
        ret = await requests.get(url, headers=header)
        if ret.status != 200:
            raise BadRequestToExternalAPI(ret.status, ret.text, url)
        ret = ret.json()

        def get_repo_dict(r):
            return {'name': r['name'],
                    'id': r['id'],
                    'full_name': r['name_with_namespace'],
                    'clone_url': r['http_url_to_repo']}

        repos = [get_repo_dict(r) for r in ret]
        return repos

    async def create_webhook(self, repo_external_id):
        """Creates a webhook at gitlab for a given repository.

        :param repo_external_id: The repository's id on gitlab.
        """
        self.log('Creating webhook to {}'.format(repo_external_id))

        header = await self._get_header()
        callback_url = settings.INTEGRATIONS_HTTP_URL + \
            'gitlab/webhooks?installation_id={}'.format(str(self.id))
        body = {'id': repo_external_id,
                'url': callback_url,
                'push_events': True,
                'merge_requests_events': True,
                'token': settings.GITLAB_WEBHOOK_TOKEN}

        url = settings.GITLAB_API_URL + 'projects/{}/hooks'.format(
            repo_external_id)
        ret = await requests.post(url, data=body, headers=header)

        if ret.status not in [200, 201]:
            raise BadRequestToExternalAPI(ret.status, ret.text)
        return True

    async def import_repository(self, repo_info, clone=True):
        r = await super().import_repository(repo_info, clone=clone)
        await self.create_webhook(repo_info['id'])
        return r
