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

import asyncio
import datetime
import json
import os
import time
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from toxicbuild.master import repository
from toxicbuild.integrations import github
from tests import async_test, AsyncMagicMock
from tests.unit.integrations import INTEGRATIONS_DATA_PATH


class GitHubAppTest(TestCase):

    def setUp(self):
        self.now = int(time.time())

    @async_test
    async def tearDown(self):
        await github.GithubApp.drop_collection()

    @patch.object(github.GithubApp, 'app_exists', AsyncMagicMock(
        return_value=True))
    @async_test
    async def test_create_app_already_exists(self):
        with self.assertRaises(github.AppExists):
            await github.GithubApp.create_app('some-id')

    @patch.object(github.GithubApp, 'app_exists', AsyncMagicMock(
        return_value=False))
    @async_test
    async def test_create_app(self):
        app = await github.GithubApp.create_app('123234')
        self.assertTrue(app.id)

    @patch.object(github.jwt, 'encode', Mock(spec=github.jwt.encode))
    @patch.object(github.time, 'time', Mock(spec=github.time.time))
    @patch.object(github.GithubApp, 'private_key', 'some/path/to/pk')
    @patch.object(github, 'open', MagicMock())
    @async_test
    async def test_create_jwt(self):
        github.time.time.return_value = self.now
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'secret-key'
        expected_payload = {'iat': self.now, 'exp': self.now + (10 * 60),
                            'iss': 1234}
        app = github.GithubApp(app_id=1234)
        await app.save()
        await github.GithubApp._create_jwt()
        expected = (expected_payload, 'secret-key', 'RS256')
        called = github.jwt.encode.call_args[0]
        self.assertEqual(expected, called)

    @async_test
    async def test_app_exists_do_not_exist(self):
        self.assertFalse(await github.GithubApp.app_exists())

    @async_test
    async def test_app_exists(self):
        app = github.GithubApp(app_id=1234)
        await app.save()
        self.assertTrue(await github.GithubApp.app_exists())

    @patch.object(github.GithubApp, '_create_jwt', AsyncMagicMock(
        return_value='myjwt'))
    @patch.object(github.requests, 'post', AsyncMagicMock(return_value=Mock()))
    @async_test
    async def test_create_installation_token(self):
        app = github.GithubApp(app_id=1234)
        await app.save()

        rdict = {"token": "v1.1f699f1069f60xxx",
                 "expires_at": "2016-07-11T22:14:10Z"}
        github.requests.post.return_value.json.return_value = rdict
        expected_header = {
            'Authorization': 'Bearer myjwt',
            'Accept': 'application/vnd.github.machine-man-preview+json'}

        installation = AsyncMagicMock()
        installation.github_id = 1234
        installation = await github.GithubApp.create_installation_token(
            installation)
        called_header = github.requests.post.call_args[1]['header']
        self.assertEqual(expected_header, called_header)
        self.assertEqual(installation.token, rdict['token'])

    @async_test
    async def test_create_installation_token_no_app(self):
        installation = Mock()
        with self.assertRaises(github.AppDoesNotExist):
            await github.GithubApp.create_installation_token(installation)


class GithubInstallationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = github.User(email='bla@bla.com')
        self.user.set_password('1234')
        await self.user.save()
        self.installation = github.GithubInstallation(user=self.user,
                                                      github_id=1234)
        await self.installation.save()

    @async_test
    async def tearDown(self):
        await github.User.drop_collection()
        await github.Repository.drop_collection()
        await github.Slave.drop_collection()
        await github.GithubInstallation.drop_collection()

    @patch.object(github.GithubInstallation, 'import_repositories',
                  AsyncMagicMock())
    @async_test
    async def test_create(self):
        install = await github.GithubInstallation.create(1234, self.user)
        self.assertTrue(install.id)
        self.assertTrue(install.import_repositories.called)

    @patch.object(github, 'now', Mock())
    def test_token_is_expired_not_expired(self):
        self.installation.expires = datetime.datetime.now()
        github.now.return_value = (self.installation.expires -
                                   datetime.timedelta(seconds=60))
        self.assertFalse(self.installation.token_is_expired)

    @patch.object(github, 'now', Mock())
    def test_token_is_expired(self):
        self.installation.expires = datetime.datetime.now()
        github.now.return_value = (self.installation.expires +
                                   datetime.timedelta(seconds=60))
        self.assertTrue(self.installation.token_is_expired)

    def test_auth_token_url(self):
        url = 'https://api.github.com/installations/{}/access_tokens'.format(
            str(self.installation.id))
        self.assertEqual(self.installation.auth_token_url, url)

    @async_test
    async def test_import_repositories(self):
        self.installation.list_repos = AsyncMagicMock(return_value=[
            Mock(), Mock()])
        self.installation.import_repository = AsyncMagicMock()
        await self.installation.import_repositories()
        self.assertEqual(
            len(self.installation.import_repository.call_args_list), 2)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, 'update_code', AsyncMagicMock())
    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @async_test
    async def test_import_repository(self):
        await github.Slave.create(name='my-slave',
                                  token='123', host='localhost',
                                  port=123, owner=self.user)
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234}
        repo = await self.installation.import_repository(repo_info)
        self.assertTrue(repo.id)
        self.assertTrue(repo.update_code.called)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @async_test
    async def test_get_header_no_token(self):

        def cmock(installation):
            installation.auth_token = 'auth-token'

        github.GithubApp.create_installation_token = asyncio.coroutine(cmock)
        self.installation.auth_token = None
        expected = 'token auth-token'
        header = await self.installation._get_header()
        self.assertEqual(header['Authorization'], expected)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @patch.object(github.GithubInstallation, 'token_is_expired', True)
    @async_test
    async def test_get_header_token_expired(self):

        def cmock(installation):
            installation.auth_token = 'new-auth-token'

        github.GithubApp.create_installation_token = asyncio.coroutine(cmock)
        self.installation.auth_token = 'auth-token'
        expected = 'token new-auth-token'
        header = await self.installation._get_header()
        self.assertEqual(header['Authorization'], expected)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @patch.object(github.GithubInstallation, 'token_is_expired', False)
    @async_test
    async def test_get_header(self):
        self.installation.auth_token = 'auth-token'
        expected = 'token auth-token'
        header = await self.installation._get_header()
        self.assertEqual(header['Authorization'], expected)
        self.assertFalse(github.GithubApp.create_installation_token.called)

    @patch.object(github.GithubInstallation, '_get_header', AsyncMagicMock(
        return_value={}))
    @patch.object(github.requests, 'post', AsyncMagicMock())
    @async_test
    async def test_list_repos(self):
        ret = github.requests.post.return_value
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'github-list-repos.json')
        with open(json_file) as fd:
            contents = fd.read()
            json_contents = json.loads(contents)

        ret.json = Mock(return_value=json_contents)
        repos = await self.installation.list_repos()
        self.assertEqual(len(repos), 1)
