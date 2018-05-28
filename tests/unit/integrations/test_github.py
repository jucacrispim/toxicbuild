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
from toxicbuild.core.utils import now, datetime2string, localtime2utc
from toxicbuild.master import repository
from toxicbuild.master.users import User
from toxicbuild.integrations import github
from tests import async_test, AsyncMagicMock, create_autospec
from tests.unit.integrations import INTEGRATIONS_DATA_PATH


class GitHubAppTest(TestCase):

    def setUp(self):
        self.dt_now = github.now()
        self.now = int(self.dt_now.timestamp())

    @async_test
    async def tearDown(self):
        await github.GithubApp.drop_collection()
        await github.GithubInstallation.drop_collection()

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

    @patch.object(github.GithubApp, 'get_jwt_token', AsyncMagicMock(
        return_value='myjwt'))
    @patch.object(github, 'settings', Mock())
    @patch.object(github, 'open', MagicMock())
    @patch.object(github.requests, 'post', AsyncMagicMock(return_value=Mock()))
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

        installation = AsyncMagicMock()
        installation.id = 'someid'
        installation.github_id = 1234
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'token'
        installation = await github.GithubApp.create_installation_token(
            installation)
        called_header = github.requests.post.call_args[1]['headers']
        self.assertEqual(expected_header, called_header)
        self.assertEqual(installation.token, rdict['token'])

    @patch.object(github.GithubApp, 'get_jwt_token', AsyncMagicMock(
        return_value='myjwt'))
    @patch.object(github, 'settings', Mock())
    @patch.object(github, 'open', MagicMock())
    @patch.object(github.requests, 'post', AsyncMagicMock(return_value=Mock()))
    @async_test
    async def test_create_installation_token_bad_response(self):
        github.requests.post.return_value.status = 400
        github.settings.GITHUB_APP_ID = 123
        github.settings.GITHUB_PRIVATE_KEY = '/some/pk'
        github.settings.GITHUB_WEBHOOK_TOKEN = 'secret'
        rdict = {"token": "v1.1f699f1069f60xxx",
                 "expires_at": "2016-07-11T22:14:10Z"}
        github.requests.post.return_value.json.return_value = rdict
        installation = AsyncMagicMock()
        read = github.open.return_value.__enter__.return_value.read
        read.return_value = 'token'
        installation.id = 'someid'
        installation.github_id = 1234
        with self.assertRaises(github.BadRequestToGithubAPI):
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

    @patch.object(github.GithubApp, 'create_token', AsyncMagicMock(
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

    @patch.object(github.GithubApp, '_create_jwt', AsyncMagicMock(
        return_value='somejwt', spec=github.GithubApp._create_jwt))
    @patch.object(github.requests, 'post', AsyncMagicMock(
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
        sig = b'invalid'
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
        sig = b'sha1=' + github.hmac.new(
            app.webhook_token.encode(), data,
            github.hashlib.sha256).digest()
        eq = app.validate_token(sig, data)
        self.assertTrue(eq)


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
    @patch.object(repository.Repository, 'update_code', AsyncMagicMock(
        spec=repository.Repository.update_code))
    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @async_test
    async def test_import_repository(self):
        await github.Slave.create(name='my-slave',
                                  token='123', host='localhost',
                                  port=123, owner=self.user)
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        repo = await self.installation.import_repository(repo_info)
        self.assertTrue(repo.id)
        self.assertTrue(repo.update_code.called)
        install = await type(self.installation).objects.get(
            id=self.installation.id)
        self.assertTrue(install.repositories)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_create_locks', AsyncMagicMock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(repository.Repository, 'update_code', AsyncMagicMock(
        spec=repository.Repository.update_code))
    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(github.GithubApp, 'create_installation_token',
                  AsyncMagicMock())
    @async_test
    async def test_import_repository_no_clone(self):
        await github.Slave.create(name='my-slave',
                                  token='123', host='localhost',
                                  port=123, owner=self.user)
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        repo = await self.installation.import_repository(repo_info,
                                                         clone=False)
        self.assertTrue(repo.id)
        self.assertFalse(repo.update_code.called)
        install = await type(self.installation).objects.get(
            id=self.installation.id)
        self.assertTrue(install.repositories)

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
        install_repo = github.GithubInstallationRepository(
            github_id=1234, repository_id=str(repo.id), full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.update_repository(1234)
        self.assertTrue(repository.Repository.update_code.called)

    @patch.object(repository, 'scheduler_action', AsyncMagicMock(
        spec=repository.scheduler_action))
    @patch.object(repository.Repository, '_delete_locks', AsyncMagicMock(
        spec=repository.Repository._delete_locks))
    @patch.object(repository.shutil, 'rmtree', Mock(
        spec=repository.shutil.rmtree))
    @async_test
    async def test_remove_repository(self):
        repo = repository.Repository(name='myrepo', url='git@bla.com/bla.git',
                                     update_seconds=10, schedule_poller=False,
                                     vcs_type='git',
                                     owner=self.user)
        await repo.save()
        install_repo = github.GithubInstallationRepository(
            github_id=1234, repository_id=str(repo.id), full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.remove_repository(1234)
        with self.assertRaises(repository.Repository.DoesNotExist):
            await repository.Repository.objects.get(id=repo.id)

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
        install_repo = github.GithubInstallationRepository(
            github_id=12345, repository_id=repo.id, full_name='a/b')
        self.installation.repositories.append(install_repo)
        install_repo = github.GithubInstallationRepository(
            github_id=1234, repository_id=repo.id, full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.update_repository(1234)
        self.assertTrue(repository.Repository.update_code.called)

    @async_test
    async def test_get_repo_by_github_id_bad_repo(self):
        with self.assertRaises(github.BadRepository):
            await self.installation._get_repo_by_github_id(123)

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

    @patch.object(github, 'settings', Mock())
    def test_get_import_chunks(self):
        github.settings.PARALLEL_IMPORTS = 1
        repos = [Mock(), Mock()]
        chunks = self.installation._get_import_chunks(repos)
        self.assertEqual(len(list(chunks)), 2)

    @async_test
    async def test_repo_request_build(self):
        github_repo_id = 'some-repo'
        branch = 'master'
        named_tree = '123adf'
        repo = AsyncMagicMock(spec=github.Repository)
        repo.start_build = create_autospec(
            spec=github.Repository().start_build, mock_cls=AsyncMagicMock)
        self.installation._get_repo_by_github_id = create_autospec(
            spec=self.installation._get_repo_by_github_id,
            mock_cls=AsyncMagicMock)
        self.installation._get_repo_by_github_id.return_value = repo
        await self.installation.repo_request_build(github_repo_id, branch,
                                                   named_tree)

        self.assertTrue(repo.request_build.called)


class GithubCheckRunTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = User(email='a@a.com')
        await self.user.save()
        self.installation = github.GithubInstallation(
            github_id=1234, user=self.user)
        await self.installation.save()

        self.repo = repository.Repository(
            name='myrepo', url='git@bla.com/bla.git',
            update_seconds=10, schedule_poller=False,
            vcs_type='git',
            owner=self.user)
        await self.repo.save()
        install_repo = github.GithubInstallationRepository(
            github_id=1234,
            repository_id=str(self.repo.id),
            full_name='a/a')

        self.installation.repositories.append(install_repo)
        await self.installation.save()
        self.check_run = github.GithubCheckRun(installation=self.installation)

    @async_test
    async def tearDown(self):
        await User.drop_collection()
        await repository.Repository.drop_collection()
        await github.GithubInstallation.drop_collection()

    @async_test
    async def test_get_repo_full_name(self):

        expected = 'a/a'
        full_name = await self.check_run._get_repo_full_name(self.repo)
        self.assertEqual(full_name, expected)

    @async_test
    async def test_get_repo_full_name_bad_repo(self):
        with self.assertRaises(github.BadRepository):
            await self.check_run._get_repo_full_name(Mock())

    @patch.object(github.BuildSet, 'objects', AsyncMagicMock())
    @async_test
    async def test_run(self):
        sender = MagicMock()
        info = {'status': 'fail', 'id': 'some-id'}
        self.check_run._send_message = AsyncMagicMock(
            spec=self.check_run._send_message)

        await self.check_run.run(sender, info)
        self.assertTrue(self.check_run._send_message.called)

    def test_get_payload(self):
        buildset = Mock()
        buildset.branch = 'master'
        buildset.commit = '123asdf'
        buildset.started = None
        run_status = 'pending'
        conclusion = None
        expected = {'name': self.check_run.run_name,
                    'head_branch': buildset.branch,
                    'head_sha': buildset.commit,
                    'status': run_status}
        payload = self.check_run._get_payload(buildset, run_status, conclusion)
        self.assertEqual(payload, expected)

    def test_get_payload_completed(self):
        buildset = Mock()
        buildset.branch = 'master'
        buildset.commit = '123asdf'
        buildset.started = localtime2utc(now())
        buildset.finished = localtime2utc(now())
        run_status = 'completed'
        started_at = datetime2string(
            buildset.started,
            dtformat="%Y-%m-%dT%H:%M:%S%z").replace('+0000', 'Z')
        completed_at = datetime2string(
            buildset.finished,
            dtformat="%Y-%m-%dT%H:%M:%S%z").replace('+0000', 'Z')
        conclusion = None
        expected = {'name': self.check_run.run_name,
                    'head_branch': buildset.branch,
                    'head_sha': buildset.commit,
                    'started_at': started_at,
                    'status': run_status,
                    'completed_at': completed_at,
                    'conclusion': conclusion}
        payload = self.check_run._get_payload(buildset, run_status, conclusion)
        self.assertEqual(payload, expected)

    @patch.object(github.requests, 'post', AsyncMagicMock(
        spec=github.requests.post))
    @patch.object(github.GithubInstallation, '_get_header', AsyncMagicMock(
        spec=github.GithubInstallation._get_header))
    @async_test
    async def test_send_message(self):
        buildset = github.BuildSet(repository=self.repo)
        buildset.branch = 'master'
        buildset.commit = '123asdf'
        buildset.started = now()
        buildset.finished = now()
        run_status = 'completed'
        conclusion = None
        github.requests.post.return_value.text = ''

        await self.check_run._send_message(buildset, run_status, conclusion)
        self.assertTrue(github.requests.post.called)
