# -*- coding: utf-8 -*-

# Copyright 2018-2019, 2023 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
import datetime
import json
import os
from unittest import TestCase
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from toxicbuild.integrations import github, base
from tests import async_test
from tests.unit.integrations import INTEGRATIONS_DATA_PATH


class GitHubAppTest(TestCase):

    def setUp(self):
        self.dt_now = github.now()
        self.now = int(self.dt_now.timestamp())

    @async_test
    async def tearDown(self):
        await github.GithubApp.drop_collection()
        await github.GithubIntegration.drop_collection()

    @patch.object(github.jwt, 'encode', Mock(spec=github.jwt.encode,
                                             return_value=b'retval'))
    @patch.object(github, 'now', Mock(spec=github.now))
    @patch.object(github, 'open', MagicMock())
    @patch.object(github, 'settings', Mock())
    @async_test
    async def test_create_jwt(self):
        github.settings.GITHUB_PRIVATE_KEY = 'some/path/to/pk'
        github.settings.GITHUB_APP_ID = 1234
        github.settings.GITHUB_WEBHOOK_TOKEN = 'secret'
        github.now.return_value = self.dt_now
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'secret-key'
        expected_payload = {'iat': self.now, 'exp': self.now + (10 * 59),
                            'iss': 1234}
        app = await github.GithubApp.get_app()
        await app._create_jwt()
        expected = (expected_payload, 'secret-key', 'RS256')
        called = github.jwt.encode.call_args[0]
        self.assertEqual(expected, called)

    @patch.object(github, 'settings', Mock())
    @patch.object(github, 'open', MagicMock())
    @patch.object(github.requests, 'post', AsyncMock(return_value=Mock()))
    @async_test
    async def test_create_app(self):
        github.settings.GITHUB_APP_ID = 123
        github.settings.GITHUB_PRIVATE_KEY = '/some/pk'
        github.settings.GITHUB_WEBHOOK_TOKEN = 'secret'
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'token'

        app = await github.GithubApp.create_app()

        self.assertTrue(app.id)

    @patch.object(github.GithubApp, 'get_jwt_token', AsyncMock(
        return_value='myjwt'))
    @patch.object(github, 'settings', Mock())
    @patch.object(github, 'open', MagicMock())
    @patch.object(github.requests, 'post', AsyncMock(return_value=Mock()))
    @async_test
    async def test_create_installation_token(self):
        github.requests.post.return_value.status = 201
        github.settings.GITHUB_APP_ID = 123
        github.settings.GITHUB_PRIVATE_KEY = '/some/pk'
        github.settings.GITHUB_WEBHOOK_TOKEN = 'secret'
        rdict = {"token": "v1.1f699f1069f60xxx",
                 "expires_at": "2016-07-11T22:14:10Z"}
        github.requests.post.return_value.json.return_value = rdict
        expected_header = {
            'Authorization': 'Bearer myjwt',
            'Accept': 'application/vnd.github.machine-man-preview+json'}

        installation = AsyncMock()
        installation.id = 'someid'
        installation.github_id = 1234
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'token'

        installation = await github.GithubApp.create_installation_token(
            installation)
        called_header = github.requests.post.call_args[1]['headers']
        self.assertEqual(expected_header, called_header)
        self.assertEqual(installation.access_token, rdict['token'])

    @patch.object(github.GithubApp, 'get_jwt_token', AsyncMock(
        return_value='myjwt'))
    @patch.object(github, 'settings', Mock())
    @patch.object(github, 'open', MagicMock())
    @patch.object(github.requests, 'post', AsyncMock(return_value=Mock()))
    @async_test
    async def test_create_installation_token_bad_response(self):
        github.requests.post.return_value.status = 400
        github.settings.GITHUB_APP_ID = 123
        github.settings.GITHUB_PRIVATE_KEY = '/some/pk'
        github.settings.GITHUB_WEBHOOK_TOKEN = 'secret'
        rdict = {"token": "v1.1f699f1069f60xxx",
                 "expires_at": "2016-07-11T22:14:10Z"}
        github.requests.post.return_value.json.return_value = rdict
        installation = AsyncMock()
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'token'
        installation.id = 'someid'
        installation.github_id = 1234
        with self.assertRaises(github.BadRequestToExternalAPI):
            installation = await github.GithubApp.create_installation_token(
                installation)

    @async_test
    async def test_is_expired_not_expired(self):
        expires = github.localtime2utc(github.now()) + datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires, private_key='bla',
                               app_id=123)
        await app.save()
        self.assertFalse(await app.is_expired())

    @async_test
    async def test_is_expired_already_expired(self):
        expires = github.localtime2utc(github.now()) - datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires, private_key='bla',
                               app_id=123)
        await app.save()
        self.assertTrue(await app.is_expired())

    @async_test
    async def test_get_jwt_token(self):
        expires = github.localtime2utc(github.now()) + datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires, jwt_token='something',
                               private_key='bla', app_id=123)
        await app.save()

        token = await app.get_jwt_token()
        self.assertEqual(token, 'something')

    @patch.object(github.GithubApp, 'create_token', AsyncMock(
        spec=github.GithubApp.create_token))
    @async_test
    async def test_get_jwt_token_create(self):
        expires = github.localtime2utc(github.now()) - datetime.timedelta(
            seconds=3600)
        app = github.GithubApp(jwt_expires=expires, jwt_token='something',
                               private_key='pk', app_id=123)
        await app.save()

        await app.get_jwt_token()
        self.assertTrue(github.GithubApp.create_token.called)

    @async_test
    async def test_set_jwt_token(self):
        app = github.GithubApp(private_key='pk', app_id=123)
        await app.save()
        await app.set_jwt_token('sometoken')
        await app.reload()
        self.assertEqual(app.jwt_token, 'sometoken')

    @async_test
    async def test_set_expire_time(self):
        app = github.GithubApp(private_key='pk', app_id=123)
        await app.save()
        await app.set_expire_time(
            github.localtime2utc(github.now()))

        await app.reload()
        self.assertTrue(app.jwt_expires)

    @patch.object(github, 'settings', Mock())
    @patch.object(github, 'open', MagicMock())
    @async_test
    async def test_get_app_already_exists(self):
        github.settings.GITHUB_APP_ID = 123
        github.settings.GITHUB_PRIVATE_KEY = '/some/pk'
        github.settings.GITHUB_WEBHOOK_TOKEN = 'secret'
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'pk'
        app = await github.GithubApp.get_app()
        rapp = await github.GithubApp.get_app()
        self.assertEqual(app, rapp)

    @async_test
    async def test_get_api_url(self):
        app = github.GithubApp(private_key='bla', app_id=123)
        await app.save()
        self.assertEqual(app.get_api_url(),
                         'https://api.github.com/app')

    @patch.object(github.GithubApp, '_create_jwt', AsyncMock(
        return_value='somejwt', spec=github.GithubApp._create_jwt))
    @patch.object(github.requests, 'post', AsyncMock(
        spec=github.requests.post))
    @async_test
    async def test_create_token(self):
        app = github.GithubApp(private_key='bla', app_id=123)
        await app.save()
        expected = {
            'Authorization': 'Bearer somejwt',
            'Accept': 'application/vnd.github.machine-man-preview+json'}
        await app.create_token()
        called = github.requests.post.call_args[1]['headers']
        self.assertEqual(called, expected)

    @async_test
    async def test_validate_token_bad_sig(self):
        sig = 'invalid'
        data = json.dumps({'some': 'payload'}).encode()
        app = github.GithubApp(private_key='bla', app_id=123,
                               webhook_token='bla')
        await app.save()
        with self.assertRaises(github.BadSignature):
            app.validate_token(sig, data)

    @async_test
    async def test_validate_token(self):
        app = github.GithubApp(private_key='bla', app_id=123,
                               webhook_token='wht')
        await app.save()
        data = json.dumps({'some': 'payload'}).encode()
        sig = 'sha1=' + github.hmac.new(
            app.webhook_token.encode(), data,
            github.hashlib.sha1).hexdigest()
        sig = sig.encode()
        eq = app.validate_token(sig, data)
        self.assertTrue(eq)


class GithubIntegrationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = base.UserInterface(None, dict(email='bla@bla.com',
                                                  id='some-id',
                                                  name='bla'))
        self.installation = github.GithubIntegration(user_id=self.user.id,
                                                     user_name=self.user.name,
                                                     github_id=1234)
        await self.installation.save()

    @async_test
    async def tearDown(self):
        await github.GithubApp.drop_collection()
        await github.GithubIntegration.drop_collection()

    def test_access_token_url(self):
        url = 'https://api.github.com/app/installations/{}/access_tokens'.\
            format(str(self.installation.github_id))
        self.assertEqual(self.installation.access_token_url, url)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMock())
    @async_test
    async def test_get_header_no_token(self):

        def cmock(installation):
            installation.access_token = 'auth-token'

        github.GithubApp.create_installation_token = asyncio.coroutine(cmock)
        self.installation.access_token = None
        expected = 'token auth-token'
        header = await self.installation.get_header()
        self.assertEqual(header['Authorization'], expected)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMock())
    @patch.object(github.GithubIntegration, 'token_is_expired', True)
    @async_test
    async def test_get_header_token_expired(self):

        def cmock(installation):
            installation.access_token = 'new-auth-token'

        github.GithubApp.create_installation_token = asyncio.coroutine(cmock)
        self.installation.access_token = 'auth-token'
        expected = 'token new-auth-token'
        header = await self.installation.get_header()
        self.assertEqual(header['Authorization'], expected)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMock())
    @patch.object(github.GithubIntegration, 'token_is_expired', False)
    @async_test
    async def test_get_header(self):
        self.installation.access_token = 'auth-token'
        expected = 'token auth-token'
        header = await self.installation.get_header()
        self.assertEqual(header['Authorization'], expected)
        self.assertFalse(github.GithubApp.create_installation_token.called)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMock(
                      spec=github.GithubApp.create_installation_token))
    @patch.object(github.GithubIntegration, 'token_is_expired', True)
    @async_test
    async def test_get_auth_url_expired_token(self):
        self.installation.access_token = 'my-token'
        url = 'https://github.com/me/somerepo.git'
        expected = 'https://x-access-token:None@github.com/me/somerepo.git'
        returned = await self.installation.get_auth_url(url)
        self.assertTrue(self.installation.app.create_installation_token.called)
        self.assertEqual(expected, returned)

    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMock(
                      spec=github.GithubApp.create_installation_token))
    @patch.object(github.GithubIntegration, 'token_is_expired', False)
    @async_test
    async def test_get_auth_url(self):
        self.installation.access_token = 'my-token'
        url = 'https://github.com/me/somerepo.git'
        expected = 'https://x-access-token:my-token@github.com/me/somerepo.git'
        returned = await self.installation.get_auth_url(url)
        self.assertFalse(
            self.installation.app.create_installation_token.called)
        self.assertEqual(expected, returned)

    @patch.object(github.GithubIntegration, 'get_header', AsyncMock(
        return_value={}))
    @patch.object(github.requests, 'get', AsyncMock())
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

    @patch.object(github.GithubIntegration, 'get_header', AsyncMock(
        return_value={}))
    @patch.object(github.requests, 'get', AsyncMock())
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
        with self.assertRaises(github.BadRequestToExternalAPI):
            await self.installation.list_repos()

    @patch.object(github.GithubIntegration, 'get_header', AsyncMock(
        return_value={}))
    @patch.object(github.requests, 'get', AsyncMock())
    @async_test
    async def test_get_repo(self):
        ret = github.requests.get.return_value
        json_file = os.path.join(INTEGRATIONS_DATA_PATH,
                                 'github-repo.json')
        with open(json_file) as fd:
            contents = fd.read()
            json_contents = json.loads(contents)

        ret.status = 200
        ret.json = Mock(return_value=json_contents)
        repo = await self.installation.get_repo(1234)
        self.assertEqual(repo['name'], 'Hello-World')

    @patch.object(github.GithubIntegration, 'get_header', AsyncMock(
        return_value={}))
    @patch.object(github.requests, 'get', AsyncMock())
    @async_test
    async def test_get_repo_bad_request(self):
        ret = github.requests.get.return_value
        ret.status = 400
        with self.assertRaises(github.BadRequestToExternalAPI):
            await self.installation.get_repo(1234)
