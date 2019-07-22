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
from unittest.mock import patch, Mock
from toxicbuild.master import repository
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


class BaseIntegrationInstallationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = base.User(email='bla@bla.com')
        self.user.set_password('1234')
        await self.user.save()
        self.installation = base.BaseIntegrationInstallation(user=self.user)

    @async_test
    async def tearDown(self):
        await base.User.drop_collection()
        await base.Repository.drop_collection()
        await base.BaseIntegrationApp.drop_collection()
        await base.Slave.drop_collection()
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

    @patch.object(base.Repository, 'schedule', Mock())
    @patch.object(base.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(base.Repository, 'request_code_update', AsyncMagicMock(
        spec=base.Repository.request_code_update))
    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @async_test
    async def test_import_repository(self):
        await base.Slave.create(name='my-slave',
                                token='123', host='localhost',
                                port=123, owner=self.user)
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

    @patch.object(base.Repository, 'schedule', Mock())
    @patch.object(base.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(base.Repository, 'update_code', AsyncMagicMock(
        spec=base.Repository.update_code))
    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @async_test
    async def test_import_repository_no_clone(self):
        await base.Slave.create(name='my-slave',
                                token='123', host='localhost',
                                port=123, owner=self.user)
        repo_info = {'name': 'my-repo', 'clone_url': 'git@github.com/bla',
                     'id': 1234, 'full_name': 'ze/my-repo'}
        self.installation._get_auth_url = AsyncMagicMock(
            return_value='https://some-url')
        self.installation.enable_notification = AsyncMagicMock()

        repo = await self.installation.import_repository(repo_info,
                                                         clone=False)
        self.assertTrue(repo.id)
        self.assertFalse(repo.update_code.called)
        install = await type(self.installation).objects.get(
            id=self.installation.id)
        self.assertTrue(install.repositories)

    @patch.object(base.Repository, 'create', AsyncMagicMock(
        side_effect=base.NotUniqueError, spec=base.Repository.create))
    @async_test
    async def test_import_repository_not_unique(self):
        await base.Slave.create(name='my-slave',
                                token='123', host='localhost',
                                port=123, owner=self.user)
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

    @patch.object(repository.Repository, 'request_code_update', AsyncMagicMock(
        spec=repository.Repository.update_code))
    @patch.object(base.BaseIntegrationInstallation, '_get_auth_url',
                  AsyncMagicMock(
                      spec=base.BaseIntegrationInstallation._get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @async_test
    async def test_update_repository(self):
        repo = repository.Repository(name='myrepo', url='git@bla.com/bla.git',
                                     update_seconds=10, schedule_poller=False,
                                     vcs_type='git',
                                     owner=self.user)
        await repo.save()
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id=str(repo.id), full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.update_repository(1234)
        self.assertTrue(repository.Repository.request_code_update.called)

    @patch.object(repository.Repository, 'request_code_update', AsyncMagicMock(
        spec=repository.Repository.update_code))
    @patch.object(base.BaseIntegrationInstallation, '_get_auth_url',
                  AsyncMagicMock(
                      spec=base.BaseIntegrationInstallation._get_auth_url,
                      return_value='https://someurl.bla/bla.git'))
    @async_test
    async def test_update_repository_same_url(self):
        repo = repository.Repository(name='myrepo', url='git@bla.com/bla.git',
                                     fetch_url='https://someurl.bla/bla.git',
                                     update_seconds=10, schedule_poller=False,
                                     vcs_type='git',
                                     owner=self.user)
        await repo.save()
        install_repo = base.ExternalInstallationRepository(
            external_id=12345, repository_id=str(repo.id), full_name='a/b')
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id=str(repo.id), full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.update_repository(1234)
        self.assertTrue(repository.Repository.request_code_update.called)

    @async_test
    async def test_repo_request_build(self):
        external_repo_id = 'some-repo'
        branch = 'master'
        named_tree = '123adf'
        repo = AsyncMagicMock(spec=base.Repository)
        repo.start_build = create_autospec(
            spec=base.Repository().start_build, mock_cls=AsyncMagicMock)
        self.installation._get_repo_by_external_id = create_autospec(
            spec=self.installation._get_repo_by_external_id,
            mock_cls=AsyncMagicMock)
        self.installation._get_repo_by_external_id.return_value = repo
        await self.installation.repo_request_build(external_repo_id, branch,
                                                   named_tree)

        self.assertTrue(repo.request_build.called)

    @patch.object(base.Repository, 'objects', AsyncMagicMock())
    @async_test
    async def test_delete(self):
        await self.installation.save()

        repo = create_autospec(spec=base.Repository,
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

        base.Repository.objects.get.side_effect = [
            base.Repository.DoesNotExist, repo]
        await self.installation.delete()
        self.assertTrue(repo.request_removal.called)

    @patch.object(repository, 'scheduler_action', AsyncMagicMock(
        spec=repository.scheduler_action))
    @patch.object(repository.shutil, 'rmtree', Mock(
        spec=repository.shutil.rmtree))
    @patch.object(repository.Repository, 'request_removal', AsyncMagicMock(
        spe=repository.Repository.request_removal))
    @async_test
    async def test_remove_repository(self):
        repo = repository.Repository(name='myrepo', url='git@bla.com/bla.git',
                                     update_seconds=10, schedule_poller=False,
                                     vcs_type='git',
                                     owner=self.user)
        await repo.save()
        install_repo = base.ExternalInstallationRepository(
            external_id=1234, repository_id=str(repo.id), full_name='a/b')
        self.installation.repositories.append(install_repo)
        await self.installation.remove_repository(1234)
        self.assertTrue(repository.Repository.request_removal.called)

    def test_get_notif_config(self):
        c = self.installation.get_notif_config()

        self.assertEqual(c['installation'], str(self.installation.id))

    @patch.object(base.Notification, 'enable', AsyncMagicMock())
    @async_test
    async def test_enable_notification(self):
        repo = Mock()
        self.installation.get_notif_config = Mock(return_value={})
        await self.installation.enable_notification(repo)

        self.assertTrue(base.Notification.enable.called)
