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
class BaseIntegrationInstallationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = base.UserInterface(None, {'email': 'bla@bla.com',
                                              'username': 'zé'})
        self.user.id = 'some-id'
        self.installation = base.BaseIntegrationInstallation(
            user_id=self.user.id, user_name=self.user.username)

    @async_test
    async def tearDown(self):
        await base.BaseIntegrationApp.drop_collection()
        await base.BaseIntegrationInstallation.drop_collection()

    @patch.object(base.BaseIntegrationInstallation, 'import_repositories',
                  AsyncMagicMock())
    @patch.object(base.BaseIntegrationInstallation, 'save', AsyncMagicMock())
    @patch.object(base.LoggerMixin, 'log_cls', Mock())
    @async_test
    async def test_create(self):

        install = await base.BaseIntegrationInstallation.create(
            self.user)
        self.assertTrue(install.import_repositories.called)
        self.assertTrue(install.save.called)

    @patch.object(base.BaseIntegrationInstallation, 'save', AsyncMagicMock())
    @patch.object(base.BaseIntegrationInstallation, 'objects', Mock())
    @patch.object(base.LoggerMixin, 'log_cls', Mock())
    @async_test
    async def test_create_install_already_exists(self):
        install = Mock()
        install.import_repositories = AsyncMagicMock()
        base.BaseIntegrationInstallation.objects.filter.\
            return_value.first = AsyncMagicMock(return_value=install)
        await base.BaseIntegrationInstallation.create(self.user)
        install = await base.BaseIntegrationInstallation.create(self.user)
        self.assertFalse(install.save.called)

    @async_test
    async def test_list_repos(self):
        with self.assertRaises(NotImplementedError):
            await self.installation.list_repos()

    @patch.object(base, 'settings', Mock())
    def test_get_import_chunks(self):
        base.settings.PARALLEL_IMPORTS = 1
        repos = [Mock(), Mock()]
        chunks = self.installation._get_import_chunks(repos)
        self.assertEqual(len(list(chunks)), 2)

    @async_test
    async def test_get_auth_url(self):
        with self.assertRaises(NotImplementedError):
            await self.installation._get_auth_url('https://some-url')

    @async_test
    async def test_import_repositories(self):
        self.installation.list_repos = AsyncMagicMock(return_value=[
            Mock(), Mock()])

        repo = Mock()
        repo.request_code_update = AsyncMagicMock()
        repo._wait_update = AsyncMagicMock()
        self.installation.import_repository = AsyncMagicMock(return_value=repo)
        await self.installation.import_repositories()
        self.assertEqual(
            len(self.installation.import_repository.call_args_list), 2)

    @patch.object(base.BaseIntegrationInstallation, 'log', Mock())
    @async_test
    async def test_import_repositories_error(self):
        self.installation.list_repos = AsyncMagicMock(return_value=[
            {'name': 'bla'}, {'name': 'ble'}])
        repo = Mock()
        repo.request_code_update = AsyncMagicMock()
        repo._wait_update = AsyncMagicMock()
        self.installation.import_repository = AsyncMagicMock(
            side_effect=[repo, Exception, False, Exception])
        repos = await self.installation.import_repositories()
        self.assertEqual(
            len(self.installation.import_repository.call_args_list), 2)
        self.assertEqual(len(repos), 1)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.SlaveInterface, 'list',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update,
                      return_value=[]))
    @async_test
    async def test_import_repository(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.installation._get_auth_url = AsyncMagicMock(
            return_value='https://some-url')

        self.installation.enable_notification = AsyncMagicMock()
        repo = await self.installation.import_repository(repo_info)
        self.assertTrue(repo.id)
        self.assertTrue(repo.request_code_update.called)
        install = await type(self.installation).objects.get(
            id=self.installation.id)
        self.assertTrue(install.repositories)

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
        self.installation._get_auth_url = AsyncMagicMock(
            return_value='https://some-url')
        self.installation.enable_notification = AsyncMagicMock()

        repo = await self.installation.import_repository(repo_info,
                                                         clone=False)
        self.assertTrue(repo.id)
        self.assertFalse(repo.request_code_update.called)
        install = await type(self.installation).objects.get(
            id=self.installation.id)
        self.assertTrue(install.repositories)

    @patch.object(base.RepositoryInterface, 'add', AsyncMagicMock(
        side_effect=base.AlreadyExists, spec=base.RepositoryInterface.add))
    @patch.object(base.SlaveInterface, 'list', AsyncMagicMock(return_value=[]))
    @async_test
    async def test_import_repository_not_unique(self):
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.installation._get_auth_url = AsyncMagicMock(
            return_value='https://some-url')

        repo = await self.installation.import_repository(repo_info,
                                                         clone=False)
        self.assertIs(repo, False)

    @async_test
    async def test_get_repo_by_exernal_id_bad_repo(self):
        with self.assertRaises(base.BadRepository):
            await self.installation._get_repo_by_external_id(123)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegrationInstallation, '_get_auth_url',
                  AsyncMagicMock(
                      spec=base.BaseIntegrationInstallation._get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @patch.object(
        base.BaseIntegrationInstallation, '_get_repo_by_external_id',
        AsyncMagicMock(
            spec=base.BaseIntegrationInstallation._get_repo_by_external_id,
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
        self.installation.repositories.append(install_repo)
        await self.installation.update_repository(1234)
        self.assertTrue(base.RepositoryInterface.request_code_update.called)

    @patch.object(base.RepositoryInterface, 'request_code_update',
                  AsyncMagicMock(
                      spec=base.RepositoryInterface.request_code_update))
    @patch.object(base.BaseIntegrationInstallation, '_get_auth_url',
                  AsyncMagicMock(
                      spec=base.BaseIntegrationInstallation._get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @patch.object(
        base.BaseIntegrationInstallation, '_get_repo_by_external_id',
        AsyncMagicMock(
            spec=base.BaseIntegrationInstallation._get_repo_by_external_id,
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
        self.installation.repositories.append(install_repo)
        await self.installation.update_repository(1234)
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
        self.installation._get_repo_by_external_id = create_autospec(
            spec=self.installation._get_repo_by_external_id,
            mock_cls=AsyncMagicMock)
        self.installation._get_repo_by_external_id.return_value = repo
        await self.installation.repo_request_build(external_repo_id, branch,
                                                   named_tree)

        self.assertTrue(repo.start_build.called)

    @patch.object(base.RepositoryInterface, 'get', AsyncMagicMock())
    @async_test
    async def test_delete(self):
        await self.installation.save()

        repo = create_autospec(spec=base.RepositoryInterface,
                               mock_cls=AsyncMagicMock)
        repo.id = 'asdf'
        gh_repo = base.ExternalInstallationRepository(
            external_id=123,
            repository_id=repo.id,
            full_name='some/name')

        self.installation.repositories.append(gh_repo)

        gh_repo = base.ExternalInstallationRepository(
            external_id=1234,
            repository_id=repo.id,
            full_name='other/name')

        self.installation.repositories.append(gh_repo)

        base.RepositoryInterface.get.side_effect = [
            base.ToxicClientException, repo]
        await self.installation.delete()
        self.assertTrue(repo.delete.called)

    @patch.object(base.RepositoryInterface, 'delete', AsyncMagicMock(
        spe=base.RepositoryInterface.delete))
    @async_test
    async def test_remove_repository(self):
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id='repo-id', full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.remove_repository(1234)
        self.assertTrue(base.RepositoryInterface.delete.called)

    def test_get_notif_config(self):
        c = self.installation.get_notif_config()

        self.assertEqual(c['installation'], str(self.installation.id))

    @patch.object(base.NotificationInterface, 'enable', AsyncMagicMock())
    @async_test
    async def test_enable_notification(self):
        repo = Mock()
        self.installation.get_notif_config = Mock(return_value={})
        await self.installation.enable_notification(repo)

        self.assertTrue(base.NotificationInterface.enable.called)
