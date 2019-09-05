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

import os
import json
from unittest import TestCase
from unittest.mock import Mock, patch
from toxicbuild.integrations import gitlab
from tests import async_test, AsyncMagicMock
from tests.unit.integrations import INTEGRATIONS_DATA_PATH


@patch.object(gitlab, 'settings', Mock(GITLAB_WEBHOOK_TOKEN='whtoken',
                                       GITLAB_APP_ID='app-id',
                                       GITLAB_APP_SECRET='app-secret'))
class GitlabAppTest(TestCase):

    @patch.object(gitlab, 'settings', Mock(GITLAB_WEBHOOK_TOKEN='whtoken',
                                           GITLAB_APP_ID='app-id',
                                           GITLAB_APP_SECRET='app-secret'))
    @async_test
    async def setUp(self):
        self.app = await gitlab.GitlabApp.create_app()

    @async_test
    async def tearDown(self):
        await gitlab.GitlabApp.drop_collection()

    @async_test
    async def test_create_app(self):
        app = await gitlab.GitlabApp.create_app()
        self.assertTrue(app.id)
        self.assertEqual(app.app_id, 'app-id')

    @async_test
    async def test_validate_token_bad(self):
        with self.assertRaises(gitlab.BadSignature):
            await self.app.validate_token('bad')

    @async_test
    async def test_validate_token(self):
        r = await self.app.validate_token('whtoken')
        self.assertTrue(r)


@patch.object(gitlab, 'settings', Mock(GITLAB_WEBHOOK_TOKEN='whtoken',
                                       GITLAB_APP_ID='app-id',
                                       GITLAB_API_URL='https://api.git.lab',
                                       GITLAB_APP_SECRET='app-secret',
                                       GITLAB_URL='https://git.lab'))
class GitlabIntegrationTest(TestCase):

    @async_test
    def setUp(self):
        self.integration = gitlab.GitlabIntegration(access_token='asdf')

    @async_test
    async def tearDown(self):
        gitlab.GitlabApp.drop_collection()
        gitlab.GitlabIntegration.drop_collection()

    @patch.object(gitlab.GitlabIntegration, 'get_headers', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.GitlabIntegration, 'request2api',
                  AsyncMagicMock(spec=gitlab.GitlabIntegration.request2api))
    @async_test
    async def test_list_repos(self):
        ret = Mock()
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'gitlab-list-repos.json')
        with open(json_file, 'rb') as fd:
            contents = fd.read().decode('utf-8')
            json_contents = json.loads(contents)

        ret.status = 200
        ret.headers = {'X-Next-Page': 0,
                       'X-Total-Pages': 1}
        ret.json = Mock(return_value=json_contents)
        gitlab.GitlabIntegration.request2api.return_value = ret

        repos = await self.integration.list_repos()
        self.assertTrue(' ' not in repos[0]['full_name'])
        self.assertEqual(len(repos), 20)

    @patch.object(gitlab.GitlabIntegration, 'get_headers', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.GitlabIntegration, 'request2api',
                  AsyncMagicMock(spec=gitlab.GitlabIntegration.request2api))
    @async_test
    async def test_create_webhook(self):
        ret = Mock()

        ret.status = 201
        gitlab.GitlabIntegration.request2api.return_value = ret
        ret = await self.integration.create_webhook(1234)
        self.assertTrue(ret)

    @patch.object(gitlab.GitlabIntegration, 'request2api',
                  AsyncMagicMock(spec=gitlab.GitlabIntegration.request2api))
    @async_test
    async def test_request_access_token(self):
        ret = Mock()
        self.integration.access_token = None
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'access_token': 'asdf',
                                 'expires_in': 7200}
        gitlab.GitlabIntegration.request2api.return_value = ret
        self.integration.get_user_id = AsyncMagicMock()
        r = await self.integration.request_access_token()
        self.assertEqual(r['access_token'], 'asdf')
        self.assertIn('expires', r)

    @patch.object(gitlab.GitlabIntegration, 'request2api',
                  AsyncMagicMock(spec=gitlab.GitlabIntegration.request2api))
    @async_test
    async def test_request_user_id(self):
        ret = Mock()
        self.integration.external_user_id = None
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'id': 666}
        gitlab.GitlabIntegration.request2api.return_value = ret
        r = await self.integration.request_user_id()
        self.assertEqual(r, 666)
