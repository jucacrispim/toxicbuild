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
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import datetime
from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock, AsyncMock

from toxicbuild.core.utils import localtime2utc
from toxicbuild.integrations import base
from tests import async_test, create_autospec


class BaseIntegrationApp(TestCase):

    def setUp(self):
        self.app = base.BaseIntegrationApp(webhook_token='token')

    @async_test
    async def test_create_app(self):
        with self.assertRaises(NotImplementedError):
            await base.BaseIntegrationApp.create_app()

    @async_test
    async def test_validate_token_bad(self):
        with self.assertRaises(base.BadSignature):
            await self.app.validate_token('bad')

    @async_test
    async def test_validate_token(self):
        r = await self.app.validate_token('token')
        self.assertTrue(r)

    @patch.object(base.BaseIntegrationApp, 'objects', Mock())
    @patch.object(base.BaseIntegrationApp, 'create_app', AsyncMock())
    @async_test
    async def test_get_app_exists(self):
        base.BaseIntegrationApp.objects.first = AsyncMock(
            return_value=Mock())
        r = await base.BaseIntegrationApp.get_app()

        self.assertTrue(r)
        self.assertFalse(base.BaseIntegrationApp.create_app.called)

    @patch.object(base.BaseIntegrationApp, 'objects', Mock())
    @patch.object(base.BaseIntegrationApp, 'create_app', AsyncMock(
        return_value=Mock()))
    @async_test
    async def test_get_app_doesnt_exist(self):
        base.BaseIntegrationApp.objects.first = AsyncMock(
            return_value=None)
        r = await base.BaseIntegrationApp.get_app()

        self.assertTrue(r)
        self.assertTrue(base.BaseIntegrationApp.create_app.called)


@patch('toxicbuild.common.client.HoleClient.connect',
       AsyncMock())
@patch('toxicbuild.common.client.HoleClient.request2server',
       AsyncMock(return_value={'id': 'asdf'}))
@patch('toxicbuild.common.client.HoleClient.is_connected', MagicMock(
    return_value=True))
@patch('toxicbuild.common.client.HoleClient.__exit__', MagicMock())
@patch('toxicbuild.common.interfaces.get_hole_client_settings',
       MagicMock(return_value={'host': 'localhost', 'port': 123,
                               'hole_token': 'asdf'}))
class BaseIntegrationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = base.UserInterface(None, {'email': 'bla@bla.com',
                                              'username': 'zé'})
        self.user.id = 'some-id'
        self.integration = base.BaseIntegration(
            user_id=self.user.id, user_name=self.user.username)

    @async_test
    async def tearDown(self):
        await base.BaseIntegrationApp.drop_collection()
        await base.BaseIntegration.drop_collection()

    @patch.object(base.BaseIntegration, 'import_repositories',
                  AsyncMock())
    @patch.object(base.BaseIntegration, 'save', AsyncMock())
    @patch.object(base.BaseIntegration, 'create_access_token',
                  AsyncMock(
                      spec=base.BaseIntegration.create_access_token))
    @patch.object(base.BaseIntegration, 'get_user_id',
                  AsyncMock(spec=base.BaseIntegration.get_user_id))
    @patch.object(base.LoggerMixin, 'log_cls', Mock())
    @async_test
    async def test_create(self):

        install = await base.BaseIntegration.create(
            self.user)
        self.assertTrue(install.import_repositories.called)
        self.assertTrue(install.save.called)
        self.assertTrue(install.create_access_token.called)
        self.assertTrue(install.get_user_id.called)

    @patch.object(base.BaseIntegration, 'save', AsyncMock())
    @patch.object(base.BaseIntegration, 'objects', Mock())
    @patch.object(base.LoggerMixin, 'log_cls', Mock())
    @async_test
    async def test_create_install_already_exists(self):
        install = Mock()
        install.import_repositories = AsyncMock()
        base.BaseIntegration.objects.filter.\
            return_value.first = AsyncMock(return_value=install)
        await base.BaseIntegration.create(self.user)
        install = await base.BaseIntegration.create(self.user)
        self.assertFalse(install.save.called)

    @async_test
    async def test_list_repos(self):
        with self.assertRaises(NotImplementedError):
            await self.integration.list_repos()

    @patch.object(base, 'settings', Mock())
    def test_get_import_chunks(self):
        base.settings.PARALLEL_IMPORTS = 1
        repos = [Mock(), Mock()]
        chunks = self.integration._get_import_chunks(repos)
        self.assertEqual(len(list(chunks)), 2)

    @async_test
    async def test_request_access_token(self):
        with self.assertRaises(NotImplementedError):
            await self.integration.request_access_token()

    @async_test
    async def test_refresh_access_token(self):
        with self.assertRaises(NotImplementedError):
            await self.integration.refresh_access_token()

    @async_test
    async def test_request_user_id(self):
        with self.assertRaises(NotImplementedError):
            await self.integration.request_user_id()

    @async_test
    async def test_get_auth_url(self):
        self.integration.access_token = 'my-token'
        self.integration.url_user = 'oauth2'
        url = 'https://gitlab.com/me/somerepo.git'
        expected = 'https://oauth2:my-token@gitlab.com/me/somerepo.git'
        returned = await self.integration.get_auth_url(url)
        self.assertEqual(expected, returned)

    @async_test
    async def test_get_auth_url_no_access_token(self):
        self.integration.access_token = None
        self.integration.url_user = 'oauth2'
        self.integration.create_access_token = AsyncMock()
        url = 'https://gitlab.com/me/somerepo.git'
        expected = 'https://oauth2:None@gitlab.com/me/somerepo.git'
        returned = await self.integration.get_auth_url(url)
        self.assertTrue(self.integration.create_access_token.called)
        self.assertEqual(expected, returned)

    @async_test
    async def test_get_auth_url_no_url_user(self):
        self.integration.url_user = None
        url = 'https://gitlab.com/me/somerepo.git'
        with self.assertRaises(base.BadRequestToExternalAPI):
            await self.integration.get_auth_url(url)

    @patch.object(base.RepositoryInterface, 'get', AsyncMock(
        spec=base.RepositoryInterface.get,
        side_effect=[
            base.RepositoryInterface(None, {'status': 'cloning', 'id': 'i'}),
            base.RepositoryInterface(None, {'status': 'ready', 'id': 'i'})]))
    @patch.object(base, 'sleep', AsyncMock())
    @async_test
    async def test_wait_clone(self):
        repo = Mock()
        repo.id = 'bla'
        await self.integration._wait_clone(repo)

        self.assertEqual(len(base.RepositoryInterface.get.call_args_list), 2)
        self.assertTrue(base.sleep.called)

    @patch.object(base.BaseIntegration, '_wait_clone',
                  AsyncMock(
                      spec=base.BaseIntegration._wait_clone))
    @async_test
    async def test_import_repositories(self):
        self.integration.list_repos = AsyncMock(return_value=[
            Mock(), Mock()])

        repo = Mock(spec=base.RepositoryInterface(None, {}))
        repo.request_code_update = AsyncMock()
        self.integration.import_repository = AsyncMock(return_value=repo)
        await self.integration.import_repositories()
        self.assertEqual(
            len(self.integration.import_repository.call_args_list), 2)

    @patch.object(base.BaseIntegration, '_wait_clone',
                  AsyncMock(
                      spec=base.BaseIntegration._wait_clone))
    @patch.object(base.BaseIntegration, 'log', Mock())
    @async_test
    async def test_import_repositories_error(self):
        self.integration.list_repos = AsyncMock(return_value=[
            {'name': 'bla'}, {'name': 'ble'}])
        repo = Mock()
        repo.request_code_update = AsyncMock()
        repo._wait_update = AsyncMock()
        self.integration.import_repository = AsyncMock(
            side_effect=[repo, Exception, False, Exception])
        repos = await self.integration.import_repositories()
        self.assertEqual(
            len(self.integration.import_repository.call_args_list), 2)
        self.assertEqual(len(repos), 1)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.SlaveInterface, 'list',
                  AsyncMock(
                      spec=base.RepositoryInterface.request_code_update,
                      return_value=[]))
    @patch.object(base.BaseIntegration, 'post_import_hooks',
                  AsyncMock(spec=base.BaseIntegration.post_import_hooks))
    @async_test
    async def test_import_repository(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMock(
            return_value='https://some-url')

        self.integration.enable_notification = AsyncMock()
        repo = await self.integration.import_repository(repo_info)
        self.assertTrue(repo.id)
        self.assertTrue(repo.request_code_update.called)
        install = await type(self.integration).objects.get(
            id=self.integration.id)
        self.assertTrue(install.repositories)
        self.assertTrue(install.post_import_hooks)

    @patch.object(base.SlaveInterface, 'list',
                  AsyncMock(
                      spec=base.SlaveInterface.list,
                      return_value=[]))
    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegration, 'create_webhook',
                  AsyncMock(spec=base.BaseIntegration.create_webhook))
    @async_test
    async def test_import_repository_no_clone(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMock(
            return_value='https://some-url')
        self.integration.enable_notification = AsyncMock()

        repo = await self.integration.import_repository(repo_info,
                                                        clone=False)
        self.assertTrue(repo.id)
        self.assertFalse(repo.request_code_update.called)
        install = await type(self.integration).objects.get(
            id=self.integration.id)
        self.assertTrue(install.repositories)

    @patch.object(base.RepositoryInterface, 'add', AsyncMock(
        side_effect=base.AlreadyExists, spec=base.RepositoryInterface.add))
    @patch.object(base.SlaveInterface, 'list', AsyncMock(return_value=[]))
    @patch.object(base.BaseIntegration, 'log', MagicMock())
    @async_test
    async def test_import_repository_not_unique(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMock(
            return_value='https://some-url')

        repo = await self.integration.import_repository(repo_info,
                                                        clone=False)
        self.assertIs(repo, False)

    @patch.object(base.RepositoryInterface, 'add', AsyncMock(
        spec=base.RepositoryInterface.add, return_value=Mock()))
    @patch.object(base.SlaveInterface, 'list', AsyncMock(return_value=[]))
    @patch.object(base.BaseIntegration, 'post_import_hooks',
                  AsyncMock(spec=base.BaseIntegration.post_import_hooks))
    @patch.object(base.BaseIntegration, 'enable_notification',
                  AsyncMock(
                      side_effect=Exception,
                      spec=base.BaseIntegration.enable_notification))
    @patch.object(base.BaseIntegration, 'log', MagicMock())
    @async_test
    async def test_import_repository_bad_notification(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMock(
            return_value='https://some-url')

        repo = await self.integration.import_repository(repo_info,
                                                        clone=False)
        self.assertTrue(base.BaseIntegration.log.called)
        self.assertTrue(repo)

    @async_test
    async def test_get_repo_by_exernal_id_bad_repo(self):
        with self.assertRaises(base.BadRepository):
            await self.integration._get_repo_by_external_id(123)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegration, 'get_auth_url',
                  AsyncMock(
                      spec=base.BaseIntegration.get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @patch.object(
        base.BaseIntegration, '_get_repo_by_external_id',
        AsyncMock(
            spec=base.BaseIntegration._get_repo_by_external_id,
            return_value=base.RepositoryInterface(
                None, {'url': 'https://someurl.bla/bla.git',
                       'fetch_url': 'https://auth@someurl.bla/bla.git'}))
    )
    @patch.object(base.RepositoryInterface, 'update',
                  AsyncMock(spec=base.RepositoryInterface.update))
    @async_test
    async def test_update_repository(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.update_repository(1234)
        self.assertTrue(base.RepositoryInterface.request_code_update.called)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegration, 'get_auth_url',
                  AsyncMock(
                      spec=base.BaseIntegration.get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @patch.object(
        base.BaseIntegration, '_get_repo_by_external_id',
        AsyncMock(
            spec=base.BaseIntegration._get_repo_by_external_id,
            return_value=base.RepositoryInterface(
                None, {'url': 'https://someurl.bla/bla.git',
                       'fetch_url': 'https://someurl.bla/bla.git'}))
    )
    @async_test
    async def test_update_repository_same_url(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=12345, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.update_repository(1234)
        self.assertTrue(base.RepositoryInterface.request_code_update.called)

    @patch.object(
        base.BaseIntegration, '_get_repo_by_external_id',
        AsyncMock(
            spec=base.BaseIntegration._get_repo_by_external_id,
            return_value=base.RepositoryInterface(
                None, {'url': 'https://someurl.bla/bla.git',
                       'fetch_url': 'https://someurl.bla/bla.git'}))
    )
    @async_test
    async def test_repo_request_build(self):
        external_repo_id = 'some-repo'
        branch = 'master'
        named_tree = '123adf'
        repo = AsyncMock(spec=base.RepositoryInterface)
        repo.start_build = AsyncMock(
            spec=base.RepositoryInterface(None, {}).start_build)
        self.integration._get_repo_by_external_id.return_value = repo
        await self.integration.repo_request_build(external_repo_id, branch,
                                                  named_tree)

        self.assertTrue(repo.start_build.called)

    @patch.object(base.RepositoryInterface, 'get', AsyncMock())
    @async_test
    async def test_delete(self):
        await self.integration.save()

        repo = create_autospec(spec=base.RepositoryInterface,
                               mock_cls=AsyncMock)
        repo.id = 'asdf'
        gh_repo = base.ExternalInstallationRepository(
            external_id=123,
            repository_id=repo.id,
            full_name='some/name')

        self.integration.repositories.append(gh_repo)

        gh_repo = base.ExternalInstallationRepository(
            external_id=1234,
            repository_id=repo.id,
            full_name='other/name')

        self.integration.repositories.append(gh_repo)

        base.RepositoryInterface.get.side_effect = [
            base.ToxicClientException, repo]
        await self.integration.delete(MagicMock())
        self.assertTrue(repo.delete.called)

    @patch.object(base.RepositoryInterface, 'delete', AsyncMock(
        spec=base.RepositoryInterface.delete))
    @async_test
    async def test_remove_repository(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.remove_repository(1234)
        self.assertTrue(base.RepositoryInterface.delete.called)

    @patch.object(base.RepositoryInterface, 'delete', AsyncMock(
        spec=base.RepositoryInterface.delete,
        side_effect=base.RepositoryDoesNotExist))
    @patch.object(base.BaseIntegration, 'log', Mock(spec=base.BaseIntegration))
    @async_test
    async def test_remove_repository_does_not_exist(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.remove_repository(1234)
        self.assertTrue(base.BaseIntegration.log.called)

    def test_get_notif_config(self):
        c = self.integration.get_notif_config()

        self.assertEqual(c['installation'], str(self.integration.id))

    @patch.object(base.NotificationInterface, 'enable', AsyncMock())
    @async_test
    async def test_enable_notification(self):
        repo = Mock()
        self.integration.get_notif_config = Mock(return_value={})
        await self.integration.enable_notification(repo)

        self.assertTrue(base.NotificationInterface.enable.called)

    @patch.object(base.BaseIntegration, 'token_is_expired', False)
    @async_test
    async def test_get_headers(self):
        self.integration.access_token = 'asdf'
        expected = {'Authorization': 'Bearer asdf'}
        r = await self.integration.get_headers()

        self.assertEqual(r, expected)

    @patch.object(base.requests, 'post', AsyncMock(
        return_value=MagicMock(status=500)))
    @async_test
    async def test_request2api_bad(self):
        meth = 'post'
        url = 'http://some.url'
        bla = 'oi'

        with self.assertRaises(base.BadRequestToExternalAPI):
            await self.integration.request2api(meth, url, bla)

    @patch.object(base.requests, 'post', AsyncMock(
        return_value=MagicMock(status=200)))
    @async_test
    async def test_request2api(self):
        meth = 'post'
        url = 'http://some.url'
        bla = 'oi'

        r = await self.integration.request2api(meth, url, bla)
        self.assertTrue(r)

    @async_test
    async def test_create_access_token(self):
        self.integration.get_user_id = AsyncMock()
        self.integration.request_access_token = AsyncMock(
            spec=self.integration.request_access_token,
            return_value={'access_token': 'token',
                          'refresh_token': 'refresh',
                          'expires': base.now()})
        await self.integration.create_access_token()
        self.assertEqual(self.integration.access_token, 'token')

    @patch.object(base.BaseIntegration, 'request_user_id',
                  AsyncMock(spec=base.BaseIntegration.request_user_id,
                                 return_value='a-user-id'))
    @async_test
    async def test_get_user_id(self):
        await self.integration.get_user_id()
        self.assertEqual(self.integration.external_user_id, 'a-user-id')

    @patch.object(base, 'settings',
                  Mock(INTEGRATIONS_HTTP_URL='https://the.url/'))
    def test_webhook_url(self):
        self.integration.id = 'the-id'
        expected = 'https://the.url/base/webhooks?installation_id=the-id'
        self.assertEqual(self.integration.webhook_url, expected)

    @patch.object(base.BaseIntegration, 'create_webhook',
                  AsyncMock(spec=base.BaseIntegration.create_webhook))
    @async_test
    async def test_post_import_hooks(self):
        await self.integration.post_import_hooks({'some': 'thing'})
        self.assertTrue(self.integration.create_webhook.called)

    @patch.object(base, 'now', Mock())
    def test_token_is_expired_not_expired(self):
        self.integration.expires = localtime2utc(
            datetime.datetime.now())
        base.now.return_value = (base.utc2localtime(
            self.integration.expires) -
            datetime.timedelta(seconds=60))
        self.assertFalse(self.integration.token_is_expired)

    @patch.object(base, 'now', Mock())
    def test_token_is_expired(self):
        self.integration.expires = localtime2utc(
            datetime.datetime.now())
        base.now.return_value = (base.utc2localtime(
            self.integration.expires) +
            datetime.timedelta(seconds=60))

        self.assertTrue(self.integration.token_is_expired)

    @patch.object(base.BaseIntegration, 'create_access_token',
                  AsyncMock(
                      spec=base.BaseIntegration.create_access_token))
    @async_test
    async def test_get_access_token_doesnt_exist(self):
        self.integration.access_token = None
        await self.integration.get_access_token()

        self.assertTrue(self.integration.create_access_token.called)

    @patch.object(base.BaseIntegration, 'refresh_access_token',
                  AsyncMock(
                      spec=base.BaseIntegration.create_access_token))
    @patch.object(base.BaseIntegration, 'token_is_expired', True)
    @async_test
    async def test_get_access_token_expired(self):
        self.integration.access_token = 'token'
        await self.integration.get_access_token()

        self.assertTrue(self.integration.refresh_access_token.called)

    @patch.object(base.BaseIntegration, 'refresh_access_token',
                  AsyncMock(
                      spec=base.BaseIntegration.create_access_token))
    @patch.object(base.BaseIntegration, 'token_is_expired', False)
    @async_test
    async def test_get_access_token(self):
        self.integration.access_token = 'token'
        await self.integration.get_access_token()

        self.assertFalse(self.integration.refresh_access_token.called)
        self.assertFalse(self.integration.refresh_access_token.called)

    def test_get_expire_dt(self):
        secs = 20
        dt = self.integration.get_expire_dt(secs)
        self.assertTrue(dt > base.now())
        self.assertTrue(dt < base.now() + base.timedelta(seconds=secs))
