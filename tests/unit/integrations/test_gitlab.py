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
        self.installation = gitlab.GitlabIntegration(access_token='asdf')

    @async_test
    async def test_get_header(self):
        expected = {'Authorization': 'Bearer asdf'}
        r = await self.installation.get_header()

        self.assertEqual(r, expected)

    @async_test
    async def test_get_header_no_access_token(self):
        expected = {'Authorization': 'Bearer None'}
        self.installation.create_access_token = AsyncMagicMock()
        self.installation.access_token = None
        r = await self.installation.get_header()

        self.assertTrue(self.installation.create_access_token.called)
        self.assertEqual(r, expected)

    @patch.object(gitlab.GitlabIntegration, 'get_header', AsyncMagicMock(
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

        repos = await self.installation.list_repos()
        self.assertTrue(' ' not in repos[0]['full_name'])
        self.assertEqual(len(repos), 20)

    @patch.object(gitlab.GitlabIntegration, 'get_header', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_list_repos_bad_request(self):
        ret = gitlab.requests.get.return_value
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'gitlab-list-repos.json')
        with open(json_file, 'rb') as fd:
            contents = fd.read().decode('utf-8')
            json_contents = json.loads(contents)

        ret.status = 404
        ret.json = Mock(return_value=json_contents)
        with self.assertRaises(gitlab.BadRequestToExternalAPI):
            await self.installation.list_repos()

    @async_test
    async def test_get_auth_url(self):
        self.installation.access_token = 'my-token'
        url = 'https://gitlab.com/me/somerepo.git'
        expected = 'https://oauth2:my-token@gitlab.com/me/somerepo.git'
        returned = await self.installation._get_auth_url(url)
        self.assertEqual(expected, returned)

    @async_test
    async def test_get_auth_url_no_access_token(self):
        self.installation.access_token = None
        self.installation.create_access_token = AsyncMagicMock()
        url = 'https://gitlab.com/me/somerepo.git'
        expected = 'https://oauth2:None@gitlab.com/me/somerepo.git'
        returned = await self.installation._get_auth_url(url)
        self.assertTrue(self.installation.create_access_token.called)
        self.assertEqual(expected, returned)

    @patch.object(gitlab.GitlabIntegration, 'get_header', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_create_webhook(self):
        ret = gitlab.requests.post.return_value

        ret.status = 200
        ret = await self.installation.create_webhook(1234)
        self.assertTrue(ret)

    @patch.object(gitlab.GitlabIntegration, 'get_header', AsyncMagicMock(
        return_value={}))
    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_create_webhook_bad_request(self):
        ret = gitlab.requests.post.return_value
        ret.status = 400
        with self.assertRaises(gitlab.BadRequestToExternalAPI):
            await self.installation.create_webhook(1234)

    @patch.object(gitlab.BaseIntegration, 'import_repository',
                  AsyncMagicMock(return_value=Mock()))
    @async_test
    async def test_import_repository(self):
        self.installation.create_webhook = AsyncMagicMock()
        await self.installation.import_repository({'id': 'bla'})

        self.assertTrue(self.installation.create_webhook.called)

    @patch.object(gitlab.BaseIntegration, 'import_repository',
                  AsyncMagicMock(return_value=False))
    @async_test
    async def test_import_repository_dont_create_webhook(self):
        self.installation.create_webhook = AsyncMagicMock()
        await self.installation.import_repository({'id': 'bla'})

        self.assertFalse(self.installation.create_webhook.called)

    @patch.object(gitlab.GitlabIntegration, 'save', AsyncMagicMock())
    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_create_access_token(self):
        ret = gitlab.requests.post.return_value
        self.installation.access_token = None
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'access_token': 'asdf'}
        self.installation.get_user_id = AsyncMagicMock()
        await self.installation.create_access_token()
        self.assertTrue(self.installation.access_token)
        self.assertTrue(self.installation.get_user_id.called)

    @patch.object(gitlab.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_create_access_token_bad_request(self):
        ret = gitlab.requests.post.return_value
        ret.status = 400
        with self.assertRaises(gitlab.BadRequestToExternalAPI):
            await self.installation.create_access_token()

    @patch.object(gitlab.GitlabIntegration, 'save', AsyncMagicMock())
    @patch.object(gitlab.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_get_user_id(self):
        ret = gitlab.requests.get.return_value
        self.installation.gitlab_user_id = None
        ret.status = 200
        ret.json = Mock()
        ret.json.return_value = {'id': 666}
        await self.installation.get_user_id()
        self.assertTrue(self.installation.gitlab_user_id)

    @patch.object(gitlab.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_get_user_id_bad_request(self):
        ret = gitlab.requests.get.return_value
        ret.status = 400
        with self.assertRaises(gitlab.BadRequestToExternalAPI):
            await self.installation.get_user_id()
