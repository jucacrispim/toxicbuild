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
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock
from toxicbuild.master import repository
from toxicbuild.integrations import github
from tests import async_test, AsyncMagicMock
from tests.unit.integrations import INTEGRATIONS_DATA_PATH


class GitHubAppTest(TestCase):

    def setUp(self):
        self.now = int(github.now().timestamp())

    @async_test
    async def tearDown(self):
        await github.GithubApp.drop_collection()
        await github.GithubInstallation.drop_collection()

    @patch.object(github.jwt, 'encode', Mock(spec=github.jwt.encode,
                                             return_value=b'retval'))
    @patch.object(github.time, 'time', Mock(spec=github.time.time))
    @patch.object(github.GithubApp, 'private_key', 'some/path/to/pk')
    @patch.object(github, 'open', MagicMock())
    @patch.object(github.GithubApp, 'app_id', 1234)
    @async_test
    async def test_create_jwt(self):
        github.time.time.return_value = self.now
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'secret-key'
        expected_payload = {'iat': self.now, 'exp': self.now + (10 * 60),
                            'iss': 1234}
        await github.GithubApp._create_jwt()
        expected = (expected_payload, 'secret-key', 'RS256')
        called = github.jwt.encode.call_args[0]
        self.assertEqual(expected, called)

    @patch.object(github.GithubApp, 'get_jwt_token', AsyncMagicMock(
        return_value='myjwt'))
    @patch.object(github.GithubApp, 'app_id', 1234)
    @patch.object(github.requests, 'post', AsyncMagicMock(return_value=Mock()))
    @async_test
    async def test_create_installation_token(self):
        github.requests.post.return_value.status = 201
        rdict = {"token": "v1.1f699f1069f60xxx",
                 "expires_at": "2016-07-11T22:14:10Z"}
        github.requests.post.return_value.json.return_value = rdict
        expected_header = {
            'Authorization': 'Bearer myjwt',
            'Accept': 'application/vnd.github.machine-man-preview+json'}

        installation = AsyncMagicMock()
        installation.id = 'someid'
        installation.github_id = 1234
        installation = await github.GithubApp.create_installation_token(
            installation)
        called_header = github.requests.post.call_args[1]['headers']
        self.assertEqual(expected_header, called_header)
        self.assertEqual(installation.token, rdict['token'])

    @async_test
    async def test_create_installation_token_no_app(self):
        installation = Mock()
        with self.assertRaises(github.AppDoesNotExist):
            await github.GithubApp.create_installation_token(installation)

    @patch.object(github.GithubApp, 'get_jwt_token', AsyncMagicMock(
        return_value='myjwt'))
    @patch.object(github.GithubApp, 'app_id', 1234)
    @patch.object(github.requests, 'post', AsyncMagicMock(return_value=Mock()))
    @async_test
    async def test_create_installation_token_bad_response(self):
        github.requests.post.return_value.status = 400
        rdict = {"token": "v1.1f699f1069f60xxx",
                 "expires_at": "2016-07-11T22:14:10Z"}
        github.requests.post.return_value.json.return_value = rdict
        installation = AsyncMagicMock()
        installation.id = 'someid'
        installation.github_id = 1234
        with self.assertRaises(github.BadRequestToGithubAPI):
            installation = await github.GithubApp.create_installation_token(
                installation)

    @async_test
    async def test_is_expired_not_expired(self):
        expires = github.localtime2utc(github.now()) + datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires)
        await app.save()
        self.assertFalse(await app.is_expired())

    @async_test
    async def test_is_expired_already_expired(self):
        expires = github.localtime2utc(github.now()) - datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires)
        await app.save()
        self.assertTrue(await app.is_expired())

    @async_test
    async def test_get_jwt_token(self):
        expires = github.localtime2utc(github.now()) + datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires, jwt_token='something')
        await app.save()

        token = await github.GithubApp.get_jwt_token()
        self.assertEqual(token, 'something')

    @patch.object(github.GithubApp, 'create_token', AsyncMagicMock(
        spec=github.GithubApp.create_token))
    @async_test
    async def test_get_jwt_token_create(self):
        expires = github.localtime2utc(github.now()) - datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires, jwt_token='something')
        await app.save()

        await github.GithubApp.get_jwt_token()
        self.assertTrue(github.GithubApp.create_token.called)

    @async_test
    async def test_set_jwt_token(self):
        app = github.GithubApp()
        await app.save()
        await github.GithubApp.set_jwt_token('sometoken')
        await app.reload()
        self.assertEqual(app.jwt_token, 'sometoken')

    @async_test
    async def test_set_expire_time(self):
        app = github.GithubApp()
        await app.save()
        await github.GithubApp.set_expire_time(
            github.localtime2utc(github.now()))

        await app.reload()
        self.assertTrue(app.jwt_expires)

    def test_get_api_url(self):
        self.assertEqual(github.GithubApp.get_api_url(),
                         'https://api.github.com/app')

    @patch.object(github.GithubApp, '_create_jwt', AsyncMagicMock(
        return_value='somejwt', spec=github.GithubApp._create_jwt))
    @patch.object(github.requests, 'post', AsyncMagicMock(
        spec=github.requests.post))
    @async_test
    async def test_create_token(self):
        app = github.GithubApp()
        await app.save()
        expected = {
            'Authorization': 'Bearer somejwt',
            'Accept': 'application/vnd.github.machine-man-preview+json'}
        await github.GithubApp.create_token()
        called = github.requests.post.call_args[1]['headers']
        self.assertEqual(called, expected)


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
        await github.GithubApp.drop_collection()
        await github.Slave.drop_collection()
        await github.GithubInstallation.drop_collection()

    @patch.object(github.GithubInstallation, 'import_repositories',
                  AsyncMagicMock())
    @async_test
    async def test_create(self):
        install = await github.GithubInstallation.create(21234, self.user)
        self.assertTrue(install.id)
        self.assertTrue(install.import_repositories.called)

    @patch.object(github.GithubInstallation, 'import_repositories',
                  AsyncMagicMock())
    @async_test
    async def test_create_install_already_exists(self):
        await github.GithubInstallation.create(21234, self.user)
        install = await github.GithubInstallation.create(21234, self.user)
        self.assertIsNone(install)

    @patch.object(github, 'now', Mock())
    def test_token_is_expired_not_expired(self):
        self.installation.expires = github.localtime2utc(
            datetime.datetime.now())
        github.now.return_value = (github.utc2localtime(
            self.installation.expires) -
            datetime.timedelta(seconds=60))
        self.assertFalse(self.installation.token_is_expired)

    @patch.object(github, 'now', Mock())
    def test_token_is_expired(self):
        self.installation.expires = github.localtime2utc(
            datetime.datetime.now())
        github.now.return_value = (github.utc2localtime(
            self.installation.expires) +
            datetime.timedelta(seconds=60))

        self.assertTrue(self.installation.token_is_expired)

    def test_auth_token_url(self):
        url = 'https://api.github.com/installations/{}/access_tokens'.format(
            str(self.installation.github_id))
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
    @patch.object(repository.Repository, '_create_locks', AsyncMagicMock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(repository.Repository, 'update_code', AsyncMagicMock())
    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
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

    @patch.object(repository.Repository, 'update_code', AsyncMagicMock(
        spec=repository.Repository.update_code))
    @patch.object(github.GithubInstallation, '_get_auth_url', AsyncMagicMock(
        spec=github.GithubInstallation._get_auth_url,
        return_value='https://someurl.bla/bla.git'))
    @async_test
    async def test_update_repository(self):
        repo = repository.Repository(name='myrepo', url='git@bla.com/bla.git',
                                     update_seconds=10, schedule_poller=False,
                                     vcs_type='git',
                                     owner=self.user)
        await repo.save()
        self.installation.repositories['1234'] = str(repo.id)
        await self.installation.update_repository('1234')
        self.assertTrue(repository.Repository.update_code.called)

    @patch.object(repository.Repository, 'update_code', AsyncMagicMock(
        spec=repository.Repository.update_code))
    @patch.object(github.GithubInstallation, '_get_auth_url', AsyncMagicMock(
        spec=github.GithubInstallation._get_auth_url,
        return_value='git@bla.com/bla.git'))
    @async_test
    async def test_update_repository_same_url(self):
        repo = repository.Repository(name='myrepo', url='git@bla.com/bla.git',
                                     fetch_url='git@bla.com/bla.git',
                                     update_seconds=10, schedule_poller=False,
                                     vcs_type='git',
                                     owner=self.user)
        await repo.save()
        self.installation.repositories['1234'] = str(repo.id)
        await self.installation.update_repository('1234')
        self.assertTrue(repository.Repository.update_code.called)

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

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @patch.object(github.GithubInstallation, 'token_is_expired', True)
    @async_test
    async def test_get_auth_url_expired_token(self):
        self.installation.auth_token = 'my-token'
        url = 'https://github.com/me/somerepo.git'
        expected = 'https://x-access-token:my-token@github.com/me/somerepo.git'
        returned = await self.installation._get_auth_url(url)
        self.assertTrue(self.installation.app.create_installation_token.called)
        self.assertEqual(expected, returned)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @patch.object(github.GithubInstallation, 'token_is_expired', False)
    @async_test
    async def test_get_auth_url(self):
        self.installation.auth_token = 'my-token'
        url = 'https://github.com/me/somerepo.git'
        expected = 'https://x-access-token:my-token@github.com/me/somerepo.git'
        returned = await self.installation._get_auth_url(url)
        self.assertFalse(
            self.installation.app.create_installation_token.called)
        self.assertEqual(expected, returned)

    @patch.object(github.GithubInstallation, '_get_header', AsyncMagicMock(
        return_value={}))
    @patch.object(github.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_list_repos(self):
        ret = github.requests.get.return_value
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'github-list-repos.json')
        with open(json_file) as fd:
            contents = fd.read()
            json_contents = json.loads(contents)

        ret.status = 200
        ret.json = Mock(return_value=json_contents)
        repos = await self.installation.list_repos()
        self.assertEqual(len(repos), 1)

    @patch.object(github.GithubInstallation, '_get_header', AsyncMagicMock(
        return_value={}))
    @patch.object(github.requests, 'get', AsyncMagicMock())
    @async_test
    async def test_list_repos_bad_request(self):
        ret = github.requests.get.return_value
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'github-list-repos.json')
        with open(json_file) as fd:
            contents = fd.read()
            json_contents = json.loads(contents)

        ret.status = 404
        ret.json = Mock(return_value=json_contents)
        with self.assertRaises(github.BadRequestToGithubAPI):
            await self.installation.list_repos()
