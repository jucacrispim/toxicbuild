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
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from aiohttp import BasicAuth
import re

from toxicbuild.integrations import settings
from toxicbuild.integrations.base import BaseIntegration, BaseIntegrationApp


class BitbucketApp(BaseIntegrationApp):

    @classmethod
    async def create_app(cls):
        webhook_token = settings.BITBUCKET_WEBHOOK_TOKEN
        app_id = settings.BITBUCKET_APP_ID
        secret = settings.BITBUCKET_APP_SECRET
        app = cls(app_id=app_id, webhook_token=webhook_token,
                  secret=secret)
        await app.save()
        return app

    def get_auth(self):
        auth = BasicAuth(self.app_id, self.secret)
        return auth


class BitbucketIntegration(BaseIntegration):

    APP_CLS = BitbucketApp
    url_user = 'x-token-auth'
    notif_name = 'bitbucket-commit-status'

    async def request_access_token(self):
        url = settings.BITBUCKET_URL + 'site/oauth2/access_token'
        app = await self.APP_CLS.get_app()
        auth = app.get_auth()
        sesskw = {'auth': auth}

        params = {'client_secret': app.secret,
                  'code': self.code,
                  'grant_type': 'authorization_code'}

        r = await self.request2api('post', url, sesskw=sesskw, data=params)
        r = r.json()
        r['expires'] = self.get_expire_dt(r['expires_in'])
        return r

    async def refresh_access_token(self):
        url = settings.BITBUCKET_URL + 'site/oauth2/access_token'

        app = await self.APP_CLS.get_app()
        auth = app.get_auth()
        sesskw = {'auth': auth}

        params = {'refresh_token': self.refresh_token,
                  'grant_type': 'refresh_token'}

        r = await self.request2api('post', url, sesskw=sesskw, params=params)
        r = r.json()
        self.access_token = r['access_token']
        self.expires = self.get_expire_dt(r['expires_in'])
        await self.save()

    async def request_user_id(self):
        url = settings.BITBUCKET_API_URL + 'user'
        headers = await self.get_headers()
        r = await self.request2api('get', url, headers=headers)
        return r.json()['account_id']

    async def list_repos(self):
        url = settings.BITBUCKET_API_URL + 'repositories/{}'.format(
            self.external_user_id)

        headers = await self.get_headers()
        repos = []
        while url:
            r = (await self.request2api('get', url, headers=headers)).json()
            for repo in r['values']:
                if repo['scm'] != 'git':
                    self.log(
                        'Only git currently supported. Skipping repo. Sorry.',
                        level='error')
                    continue

                repos.append(self._get_repo_dict(repo))

            url = r.get('next')

        return repos

    async def create_webhook(self, repo_info):
        """Creates a webhook at bitbucket for a given repository.

        :param repo_external_id: The repository's id at bitbucket.
        """
        app = await self.APP_CLS.get_app()

        url = self.webhook_url + '&token={}'.format(app.webhook_token)
        self.log('Creating webhook to {}'.format(repo_info['full_name']))
        self.log('With url: {}'.format(url), level='debug')

        header = await self.get_headers()
        body = {'description': 'Toxicbuild Webhook',
                'url': url,
                'active': True,
                'events': [
                    'repo:push',
                    'pullrequest:created',
                    'pullrequest:updated'
                ]}

        url = settings.BITBUCKET_API_URL + 'repositories/{}/hooks'.format(
            repo_info['full_name'])
        await self.request2api('post', url, statuses=[200, 201], data=body,
                               headers=header)
        return True

    def _get_repo_dict(self, repo_info):

        def get_clone_url(links):
            for link in links:  # pragma no branch
                if link['name'] == 'https':
                    return link['href']

        url = get_clone_url(repo_info['links']['clone'])
        # the url returned by bitbucket has a username@ in the url.
        # Remove it 'cause we use a token based auth.
        p = re.compile('\w+://(.*@).+')
        m = p.match(url).groups()[0]
        url = url.replace(m, '')
        d = {
            'id': repo_info['uuid'],
            'name': repo_info['name'],
            'full_name': repo_info['full_name'],
            'slug': repo_info['slug'],
            'clone_url': url
        }
        return d
