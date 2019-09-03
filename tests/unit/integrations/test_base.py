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

from unittest import TestCase
from unittest.mock import patch, Mock, MagicMock
from toxicbuild.integrations import base
from tests import AsyncMagicMock, async_test, create_autospec


class BaseIntegrationApp(TestCase):

    @async_test
    async def test_create_app(self):
        with self.assertRaises(NotImplementedError):
            await base.BaseIntegrationApp.create_app()

    @patch.object(base.BaseIntegrationApp, 'objects', Mock())
    @patch.object(base.BaseIntegrationApp, 'create_app', AsyncMagicMock())
    @async_test
    async def test_get_app_exists(self):
        base.BaseIntegrationApp.objects.first = AsyncMagicMock(
            return_value=Mock())
        r = await base.BaseIntegrationApp.get_app()

        self.assertTrue(r)
        self.assertFalse(base.BaseIntegrationApp.create_app.called)

    @patch.object(base.BaseIntegrationApp, 'objects', Mock())
    @patch.object(base.BaseIntegrationApp, 'create_app', AsyncMagicMock(
        return_value=Mock()))
    @async_test
    async def test_get_app_doesnt_exist(self):
        base.BaseIntegrationApp.objects.first = AsyncMagicMock(
            return_value=None)
        r = await base.BaseIntegrationApp.get_app()

        self.assertTrue(r)
        self.assertTrue(base.BaseIntegrationApp.create_app.called)


@patch('toxicbuild.common.client.HoleClient.connect',
       AsyncMagicMock())
@patch('toxicbuild.common.client.HoleClient.request2server',
       AsyncMagicMock(return_value={'id': 'asdf'}))
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
                  AsyncMagicMock())
    @patch.object(base.BaseIntegration, 'save', AsyncMagicMock())
    @patch.object(base.BaseIntegration, 'create_access_token',
                  AsyncMagicMock(
                      spec=base.BaseIntegration.create_access_token))
    @patch.object(base.BaseIntegration, 'get_user_id',
                  AsyncMagicMock(spec=base.BaseIntegration.get_user_id))
    @patch.object(base.LoggerMixin, 'log_cls', Mock())
    @async_test
    async def test_create(self):

        install = await base.BaseIntegration.create(
            self.user)
        self.assertTrue(install.import_repositories.called)
        self.assertTrue(install.save.called)
        self.assertTrue(install.create_access_token.called)
        self.assertTrue(install.get_user_id.called)

    @patch.object(base.BaseIntegration, 'save', AsyncMagicMock())
    @patch.object(base.BaseIntegration, 'objects', Mock())
    @patch.object(base.LoggerMixin, 'log_cls', Mock())
    @async_test
    async def test_create_install_already_exists(self):
        install = Mock()
        install.import_repositories = AsyncMagicMock()
        base.BaseIntegration.objects.filter.\
            return_value.first = AsyncMagicMock(return_value=install)
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
    async def test_get_user_id(self):
        with self.assertRaises(NotImplementedError):
            await self.integration.get_user_id()

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
        self.integration.create_access_token = AsyncMagicMock()
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

    @patch.object(base.RepositoryInterface, 'get', AsyncMagicMock(
        spec=base.RepositoryInterface.get,
        side_effect=[
            base.RepositoryInterface(None, {'status': 'cloning', 'id': 'i'}),
            base.RepositoryInterface(None, {'status': 'ready', 'id': 'i'})]))
    @patch.object(base, 'sleep', AsyncMagicMock())
    @async_test
    async def test_wait_clone(self):
        repo = Mock()
        repo.id = 'bla'
        await self.integration._wait_clone(repo)

        self.assertEqual(len(base.RepositoryInterface.get.call_args_list), 2)
        self.assertTrue(base.sleep.called)

    @patch.object(base.BaseIntegration, '_wait_clone',
                  AsyncMagicMock(
                      spec=base.BaseIntegration._wait_clone))
    @async_test
    async def test_import_repositories(self):
        self.integration.list_repos = AsyncMagicMock(return_value=[
            Mock(), Mock()])

        repo = Mock(spec=base.RepositoryInterface(None, {}))
        repo.request_code_update = AsyncMagicMock()
        self.integration.import_repository = AsyncMagicMock(return_value=repo)
        await self.integration.import_repositories()
        self.assertEqual(
            len(self.integration.import_repository.call_args_list), 2)

    @patch.object(base.BaseIntegration, '_wait_clone',
                  AsyncMagicMock(
                      spec=base.BaseIntegration._wait_clone))
    @patch.object(base.BaseIntegration, 'log', Mock())
    @async_test
    async def test_import_repositories_error(self):
        self.integration.list_repos = AsyncMagicMock(return_value=[
            {'name': 'bla'}, {'name': 'ble'}])
        repo = Mock()
        repo.request_code_update = AsyncMagicMock()
        repo._wait_update = AsyncMagicMock()
        self.integration.import_repository = AsyncMagicMock(
            side_effect=[repo, Exception, False, Exception])
        repos = await self.integration.import_repositories()
        self.assertEqual(
            len(self.integration.import_repository.call_args_list), 2)
        self.assertEqual(len(repos), 1)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.SlaveInterface, 'list',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update,
                      return_value=[]))
    @patch.object(base.BaseIntegration, 'post_import_hooks',
                  AsyncMagicMock(spec=base.BaseIntegration.post_import_hooks))
    @async_test
    async def test_import_repository(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMagicMock(
            return_value='https://some-url')

        self.integration.enable_notification = AsyncMagicMock()
        repo = await self.integration.import_repository(repo_info)
        self.assertTrue(repo.id)
        self.assertTrue(repo.request_code_update.called)
        install = await type(self.integration).objects.get(
            id=self.integration.id)
        self.assertTrue(install.repositories)
        self.assertTrue(install.post_import_hooks)

    @patch.object(base.SlaveInterface, 'list',
                  AsyncMagicMock(
                      spec=base.SlaveInterface.list,
                      return_value=[]))
    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @async_test
    async def test_import_repository_no_clone(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMagicMock(
            return_value='https://some-url')
        self.integration.enable_notification = AsyncMagicMock()

        repo = await self.integration.import_repository(repo_info,
                                                        clone=False)
        self.assertTrue(repo.id)
        self.assertFalse(repo.request_code_update.called)
        install = await type(self.integration).objects.get(
            id=self.integration.id)
        self.assertTrue(install.repositories)

    @patch.object(base.RepositoryInterface, 'add', AsyncMagicMock(
        side_effect=base.AlreadyExists, spec=base.RepositoryInterface.add))
    @patch.object(base.SlaveInterface, 'list', AsyncMagicMock(return_value=[]))
    @patch.object(base.BaseIntegration, 'log', MagicMock())
    @async_test
    async def test_import_repository_not_unique(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.integration.get_auth_url = AsyncMagicMock(
            return_value='https://some-url')

        repo = await self.integration.import_repository(repo_info,
                                                        clone=False)
        self.assertIs(repo, False)

    @async_test
    async def test_get_repo_by_exernal_id_bad_repo(self):
        with self.assertRaises(base.BadRepository):
            await self.integration._get_repo_by_external_id(123)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegration, 'get_auth_url',
                  AsyncMagicMock(
                      spec=base.BaseIntegration.get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @patch.object(
        base.BaseIntegration, '_get_repo_by_external_id',
        AsyncMagicMock(
            spec=base.BaseIntegration._get_repo_by_external_id,
            return_value=base.RepositoryInterface(
                None, {'url': 'https://someurl.bla/bla.git',
                       'fetch_url': 'https://auth@someurl.bla/bla.git'}))
    )
    @patch.object(base.RepositoryInterface, 'update',
                  AsyncMagicMock(spec=base.RepositoryInterface.update))
    @async_test
    async def test_update_repository(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.update_repository(1234)
        self.assertTrue(base.RepositoryInterface.request_code_update.called)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegration, 'get_auth_url',
                  AsyncMagicMock(
                      spec=base.BaseIntegration.get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @patch.object(
        base.BaseIntegration, '_get_repo_by_external_id',
        AsyncMagicMock(
            spec=base.BaseIntegration._get_repo_by_external_id,
            return_value=base.RepositoryInterface(
                None, {'url': 'https://someurl.bla/bla.git',
                       'fetch_url': 'https://someurl.bla/bla.git'}))
    )
    @async_test
    async def test_update_repository_same_url(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=12345, repository_id='repo-id', full_name='a/b')
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.update_repository(1234)
        self.assertTrue(base.RepositoryInterface.request_code_update.called)

    @async_test
    async def test_repo_request_build(self):
        external_repo_id = 'some-repo'
        branch = 'master'
        named_tree = '123adf'
        repo = AsyncMagicMock(spec=base.RepositoryInterface)
        repo.start_build = create_autospec(
            spec=base.RepositoryInterface(None, {}).start_build,
            mock_cls=AsyncMagicMock)
        self.integration._get_repo_by_external_id = create_autospec(
            spec=self.integration._get_repo_by_external_id,
            mock_cls=AsyncMagicMock)
        self.integration._get_repo_by_external_id.return_value = repo
        await self.integration.repo_request_build(external_repo_id, branch,
                                                  named_tree)

        self.assertTrue(repo.start_build.called)

    @patch.object(base.RepositoryInterface, 'get', AsyncMagicMock())
    @async_test
    async def test_delete(self):
        await self.integration.save()

        repo = create_autospec(spec=base.RepositoryInterface,
                               mock_cls=AsyncMagicMock)
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

    @patch.object(base.RepositoryInterface, 'delete', AsyncMagicMock(
        spe=base.RepositoryInterface.delete))
    @async_test
    async def test_remove_repository(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.integration.repositories.append(install_repo)
        await self.integration.remove_repository(1234)
        self.assertTrue(base.RepositoryInterface.delete.called)

    def test_get_notif_config(self):
        c = self.integration.get_notif_config()

        self.assertEqual(c['installation'], str(self.integration.id))

    @patch.object(base.NotificationInterface, 'enable', AsyncMagicMock())
    @async_test
    async def test_enable_notification(self):
        repo = Mock()
        self.integration.get_notif_config = Mock(return_value={})
        await self.integration.enable_notification(repo)

        self.assertTrue(base.NotificationInterface.enable.called)

    @async_test
    async def test_get_headers(self):
        self.integration.access_token = 'asdf'
        expected = {'Authorization': 'Bearer asdf'}
        r = await self.integration.get_headers()

        self.assertEqual(r, expected)

    @async_test
    async def test_get_headers_no_access_token(self):
        expected = {'Authorization': 'Bearer None'}
        self.integration.create_access_token = AsyncMagicMock()
        self.integration.access_token = None
        r = await self.integration.get_headers()

        self.assertTrue(self.integration.create_access_token.called)
        self.assertEqual(r, expected)

    @patch.object(base.requests, 'post', AsyncMagicMock(
        return_value=MagicMock(status=500)))
    @async_test
    async def test_request2api_bad(self):
        meth = 'post'
        url = 'http://some.url'
        bla = 'oi'

        with self.assertRaises(base.BadRequestToExternalAPI):
            await self.integration.request2api(meth, url, bla)

    @patch.object(base.requests, 'post', AsyncMagicMock(
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
        self.integration.get_user_id = AsyncMagicMock()
        self.integration.request_access_token = AsyncMagicMock(
            spec=self.integration.request_access_token,
            return_value='token')
        await self.integration.create_access_token()
        self.assertEqual(self.integration.access_token, 'token')
