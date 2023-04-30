# -*- coding: utf-8 -*-
# Copyright 2019, 2023 Juca Crispim <juca@poraodojuca.net>

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

import json
import os
from unittest import TestCase
from unittest.mock import Mock, patch, AsyncMock

from toxicbuild.integrations import bitbucket

from tests import async_test
from tests.unit.integrations import INTEGRATIONS_DATA_PATH


@patch.object(bitbucket, 'settings', Mock(
    BITBUCKET_APP_ID='app-id',
    BITBUCKET_APP_SECRET='secret',
    BITBUCKET_WEBHOOK_TOKEN='token',
    BITBUCKET_URL='https://bb.url/',
    BITBUCKET_API_URL='https://api.bb.url/'
))
class BitbucketAppTest(TestCase):

    @patch.object(bitbucket, 'settings', Mock(
        BITBUCKET_APP_ID='app-id',
        BITBUCKET_APP_SECRET='secret',
        BITBUCKET_WEBHOOK_TOKEN='token',
        BITBUCKET_URL='https://bb.url/',
        BITBUCKET_API_URL='https://api.bb.url/'
    ))
    @async_test
    async def setUp(self):
        self.app = await bitbucket.BitbucketApp.create_app()

    @async_test
    async def tearDown(self):
        await bitbucket.BitbucketApp.drop_collection()

    @async_test
    async def test_create_app(self):
        app = await bitbucket.BitbucketApp.create_app()
        self.assertTrue(app.id)

    @async_test
    async def test_get_auth(self):
        auth = self.app.get_auth()
        self.assertIsInstance(auth, bitbucket.BasicAuth)


@patch.object(bitbucket, 'settings', Mock(
    BITBUCKET_APP_ID='app-id',
    BITBUCKET_APP_SECRET='secret',
    BITBUCKET_WEBHOOK_TOKEN='token',
    BITBUCKET_URL='https://bb.url/',
    BITBUCKET_API_URL='https://api.bb.url/'
))
class BitbucketIntegrationTest(TestCase):

    def setUp(self):
        self.integration = bitbucket.BitbucketIntegration()

    @async_test
    async def tearDown(self):
        await bitbucket.BitbucketApp.drop_collection()
        await bitbucket.BitbucketIntegration.drop_collection()

    @async_test
    async def test_request_access_token(self):
        ret = Mock()
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'access_token': 'asdf',
                                 'expires_in': 7200}

        self.integration.request2api = AsyncMock(
            spec=self.integration.request2api,
            return_value=ret
        )

        self.integration.access_token = None
        r = await self.integration.request_access_token()
        self.assertEqual(r['access_token'], 'asdf')

    @patch.object(bitbucket.BitbucketIntegration, 'save', AsyncMock())
    @async_test
    async def test_refresh_access_token(self):
        bitbucket.settings.INTEGRATIONS_ADJUST_TIME = 0
        ret = Mock()
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'access_token': 'new-token',
                                 'expires_in': 7200}

        self.integration.request2api = AsyncMock(
            spec=self.integration.request2api,
            return_value=ret
        )

        await self.integration.refresh_access_token()
        self.assertEqual(self.integration.access_token, 'new-token')

    @patch.object(bitbucket.BitbucketIntegration, 'request2api',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.request2api))
    @patch.object(bitbucket.BitbucketIntegration, 'create_access_token',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.create_access_token))
    @async_test
    async def test_request_user_id(self):
        ret = Mock()
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'account_id': 'asdf',
                                 'links': {'repositories':
                                           {'href': 'https://bla'}}}
        bitbucket.BitbucketIntegration.request2api.return_value = ret

        uuid = await self.integration.request_user_id()
        url = self.integration.request2api.call_args[0][1]
        expected_url = 'https://api.bb.url/user'

        self.assertEqual(uuid, 'asdf')
        self.assertEqual(url, expected_url)

    @patch.object(bitbucket.BitbucketIntegration, 'request2api',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.request2api))
    @patch.object(bitbucket.BitbucketIntegration, 'create_access_token',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.create_access_token))
    @patch.object(bitbucket.BitbucketIntegration, 'log',
                  Mock(spec=bitbucket.BitbucketIntegration.log))
    @async_test
    async def test_list_repos(self):

        def get_json(fname):
            with open(fname, 'rb') as fd:
                contents = fd.read().decode('utf-8')
            return json.loads(contents)

        pg1_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                'bitbucket-list-repos-pg1.json')
        pg2_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                'bitbucket-list-repos-pg2.json')
        pg1, pg2 = get_json(pg1_file), get_json(pg2_file)

        ret = Mock()
        ret.status = 200
        ret.json = Mock()
        ret.json.side_effect = [pg1, pg2]
        bitbucket.BitbucketIntegration.request2api.return_value = ret
        self.integration.repo_list_url = 'https://bla'
        repos = await self.integration.list_repos()

        self.assertEqual(len(repos), 4)

    @patch.object(bitbucket.BitbucketApp, 'get_app',
                  AsyncMock(
                      spec=bitbucket.BitbucketApp.get_app,
                      return_value=bitbucket.BitbucketApp()))
    @patch.object(bitbucket.BitbucketIntegration, 'request2api',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.request2api))
    @patch.object(bitbucket.BitbucketIntegration, 'get_headers',
                  AsyncMock(
                      spec=bitbucket.BitbucketIntegration.get_headers,
                      return_value={}))
    @async_test
    async def test_create_webhook(self):
        await self.integration.create_webhook({'full_name': 'me/repo',
                                               'slug': 'repo'})
        self.assertTrue(self.integration.get_headers.called)
        self.assertTrue(self.integration.request2api.called)

    def test_get_repo_dict(self):
        repo_info = {
            'links': {
                'clone': [
                    {
                        'name': 'https',
                        'href': 'https://me@bb.com/repo.git',
                    }
                ],
            },
            'uuid': 'uuid',
            'name': 'repo',
            'full_name': 'me/repo',
            'slug': 'repo',
        }
        r = self.integration._get_repo_dict(repo_info)

        self.assertEqual(r['clone_url'], 'https://bb.com/repo.git')
