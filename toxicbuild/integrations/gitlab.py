# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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


from toxicbuild.integrations.base import BaseIntegration, BaseIntegrationApp
from toxicbuild.integrations import settings
from toxicbuild.integrations.exceptions import BadSignature

__doc__ = """This module implements integration with gitlab. Imports
repositories from GitLab and reacts to messages sent by gitlab to
toxicbuild's integrations webhook.
See: `GitLab integration docs <https://about.gitlab.com/partners/integrate/>`_.
"""


class GitlabApp(BaseIntegrationApp):

    @classmethod
    async def create_app(cls):
        webhook_token = settings.GITLAB_WEBHOOK_TOKEN
        app_id = settings.GITLAB_APP_ID
        secret = settings.GITLAB_APP_SECRET
        app = cls(app_id=app_id, webhook_token=webhook_token,
                  secret=secret)
        await app.save()
        return app

    async def validate_token(self, token):
        if token != self.webhook_token:
            raise BadSignature
        return True


class GitlabIntegration(BaseIntegration):

    APP_CLS = GitlabApp

    url_user = 'oauth2'
    notif_name = 'gitlab-commit-status'

    REDIRECT_URI = getattr(
        settings, 'INTEGRATIONS_HTTP_URL', '') + 'gitlab/setup'

    async def request_user_id(self):
        """Gets the user id from the gitlab api. Returns the id
        """
        header = await self.get_headers()
        url = settings.GITLAB_API_URL + 'user'
        r = await self.request2api('get', url, headers=header)
        return r.json()['id']

    async def request_access_token(self):
        url = settings.GITLAB_URL + 'oauth/token'
        app = await self.APP_CLS.get_app()
        params = {'client_id': app.app_id,
                  'client_secret': app.secret,
                  'code': self.code,
                  'grant_type': 'authorization_code',
                  'redirect_uri': self.REDIRECT_URI}

        r = await self.request2api('post', url, params=params)
        return r.json()['access_token']

    async def list_repos(self):
        """Lists the repositories using GitLab API.
        """

        def get_repo_dict(r):
            return {'name': r['name'],
                    'id': r['id'],
                    'full_name': r['path_with_namespace'],
                    'clone_url': r['http_url_to_repo']}

        header = await self.get_headers()
        p = 1
        repos = []
        while True:
            self.log('Fetching page {}'.format(p), level='debug')
            url = settings.GITLAB_API_URL + 'users/{}/projects?page={}'.format(
                self.external_user_id, p)

            ret = await self.request2api('get', url, headers=header)
            p += 1
            repos += [get_repo_dict(r) for r in ret.json()]

            n = ret.headers.get('X-Next-Page', 0)
            t = ret.headers.get('X-Total-Pages', 0)
            if not n or n > t:  # pragma no branch
                break

        return repos

    async def create_webhook(self, repo_external_id):
        """Creates a webhook at gitlab for a given repository.

        :param repo_external_id: The repository's id on gitlab.
        """
        self.log('Creating webhook to {}'.format(repo_external_id))

        header = await self.get_headers()
        body = {'id': repo_external_id,
                'url': self.webhook_url,
                'push_events': True,
                'merge_requests_events': True,
                'token': settings.GITLAB_WEBHOOK_TOKEN}

        url = settings.GITLAB_API_URL + 'projects/{}/hooks'.format(
            repo_external_id)
        await self.request2api('post', url, statuses=[200, 201], data=body,
                               headers=header)
        return True

    @property
    def token_is_expired(self):
        """Gitlab tokens do not expire.
        """
        return False
