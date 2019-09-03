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


class GitlabIntegrationTest(TestCase):

    @async_test
    def setUp(self):
        self.integration = gitlab.GitlabIntegration(access_token='asdf')

    @patch.object(gitlab.GitlabIntegration, 'get_headers', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_list_repos(self):
        ret = gitlab.requests.get.return_value
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'gitlab-list-repos.json')
        with open(json_file, 'rb') as fd:
            contents = fd.read().decode('utf-8')
            json_contents = json.loads(contents)

        ret.status = 200
        ret.headers = {'X-Next-Page': 0,
                       'X-Total-Pages': 1}
        ret.json = Mock(return_value=json_contents)

        repos = await self.integration.list_repos()
        self.assertTrue(' ' not in repos[0]['full_name'])
        self.assertEqual(len(repos), 20)

    @patch.object(gitlab.GitlabIntegration, 'get_headers', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_create_webhook(self):
        ret = gitlab.requests.post.return_value

        ret.status = 200
        ret = await self.integration.create_webhook(1234)
        self.assertTrue(ret)

    @patch.object(gitlab.GitlabIntegration, 'get_headers', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_create_webhook_bad_request(self):
        ret = gitlab.requests.post.return_value
        ret.status = 400
        with self.assertRaises(gitlab.BadRequestToExternalAPI):
            await self.integration.create_webhook(1234)

    @patch.object(gitlab.GitlabIntegration, 'create_webhook',
                  AsyncMagicMock(
                      spec=gitlab.GitlabIntegration.create_webhook,
                      return_value=Mock()))
    @async_test
    async def test_post_import_hooks(self):
        await self.integration.post_import_hooks('external-id')

        self.assertTrue(self.integration.create_webhook.called)

    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_request_access_token(self):
        ret = gitlab.requests.post.return_value
        self.integration.access_token = None
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'access_token': 'asdf'}
        self.integration.get_user_id = AsyncMagicMock()
        r = await self.integration.request_access_token()
        self.assertEqual(r, 'asdf')

    @patch.object(gitlab.BaseIntegration, 'create_access_token',
                  AsyncMagicMock(
                      spec=gitlab.BaseIntegration.create_access_token))
    @async_test
    async def test_create_access_token(self):
        self.integration.get_user_id = AsyncMagicMock(
            spec=self.integration.get_user_id)
        await self.integration.create_access_token()

        self.assertTrue(gitlab.BaseIntegration.create_access_token.called)
        self.assertTrue(self.integration.get_user_id.called)

    @patch.object(gitlab.GitlabIntegration, 'save', AsyncMagicMock())
    @patch.object(gitlab.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_get_user_id(self):
        ret = gitlab.requests.get.return_value
        self.integration.external_user_id = None
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'id': 666}
        await self.integration.get_user_id()
        self.assertTrue(self.integration.external_user_id)
