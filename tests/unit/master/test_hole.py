# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
from datetime import datetime
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch
from bson import ObjectId
from toxicbuild.master import hole, build, repository, slave
from tests import async_test, AsyncMagicMock, create_autospec


@patch.object(repository, 'repo_added', AsyncMagicMock())
class UIHoleTest(TestCase):

    def setUp(self):
        hole.UIHole._shutting_down = False

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_ok(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        handle = MagicMock()
        hole.HoleHandler.handle = asyncio.coroutine(lambda *a, **kw: handle())
        uihole = hole.UIHole(Mock())
        uihole._stream_writer = Mock()
        # no exception means ok
        user = hole.User(email='ze@ze.con', password='asdf')
        await user.save()
        uihole.data = {'user_id': str(user.id)}
        status = await uihole.client_connected()
        self.assertEqual(status, 0)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'close_connection', MagicMock())
    @async_test
    async def test_client_connected_shutting_down(self):
        handle = MagicMock()
        hole.HoleHandler.handle = asyncio.coroutine(lambda *a, **kw: handle())
        uihole = hole.UIHole(Mock())
        uihole._stream_writer = Mock()
        # no exception means ok
        user = hole.User(email='ze@ze.con', password='asdf')
        await user.save()
        uihole.data = {'user_id': str(user.id)}
        uihole.set_shutting_down()
        status = await uihole.client_connected()
        self.assertIsNone(status)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_user_does_not_exist(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        handle = MagicMock()
        hole.HoleHandler.handle = asyncio.coroutine(lambda *a, **kw: handle())
        uihole = hole.UIHole(Mock())
        uihole._stream_writer = Mock()
        uihole.data = {}
        status = await uihole.client_connected()
        self.assertEqual(status, 2)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_user_does_not_exist_handle(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        hole.HoleHandler.handle = AsyncMagicMock(
            side_effect=hole.User.DoesNotExist)
        uihole = hole.UIHole(Mock())
        uihole._stream_writer = Mock()
        uihole._get_user = AsyncMagicMock()
        uihole.data = {}
        status = await uihole.client_connected()
        self.assertEqual(status, 2)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_bad_reset_token(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        hole.HoleHandler.handle = AsyncMagicMock(
            side_effect=hole.ResetUserPasswordToken.DoesNotExist)
        uihole = hole.UIHole(Mock())
        uihole._stream_writer = Mock()
        uihole.log = Mock()
        uihole._get_user = AsyncMagicMock()
        uihole.data = {}
        status = await uihole.client_connected()
        self.assertEqual(status, 4)

    @patch.object(hole, 'UIStreamHandler', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_with_stream(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        uihole = hole.UIHole(Mock())
        uihole.action = 'stream'
        uihole._stream_writer = Mock()

        user = hole.User(email='ze@ze.nada', password='asdf')
        await user.save()
        uihole.data = {'user_id': str(user.id)}

        await uihole.client_connected()

        self.assertTrue(hole.UIStreamHandler.called)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_error(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))

        @asyncio.coroutine
        def handle(*a, **kw):
            raise Exception('bla')

        user = hole.User(email='ze@ndad.con', password='asdf')
        await user.save()
        hole.HoleHandler.handle = handle
        uihole = hole.UIHole(Mock())
        uihole.data = {'user_id': str(user.id)}
        uihole._stream_writer = Mock()

        await uihole.client_connected()

        response = send_response.call_args[1]
        response_code = response['code']
        self.assertEqual(response_code, 1, response)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_not_enough_perms(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))

        @asyncio.coroutine
        def handle(*a, **kw):
            raise hole.NotEnoughPerms

        user = hole.User(email='ze@ndad.con', password='asdf')
        await user.save()
        hole.HoleHandler.handle = handle
        uihole = hole.UIHole(Mock())
        uihole.data = {'user_id': str(user.id)}
        uihole._stream_writer = Mock()

        await uihole.client_connected()

        response = send_response.call_args[1]
        response_code = response['code']
        self.assertEqual(response_code, 3, response)

    @patch.object(hole.HoleHandler, 'user_authenticate', AsyncMagicMock())
    @patch.object(hole.UIHole, 'send_response', AsyncMagicMock())
    @async_test
    async def test_client_connected_authenticate(self):
        user = hole.User(email='ze@ndad.con', password='asdf')
        await user.save()
        uihole = hole.UIHole(Mock())
        uihole.data = {'user_id': str(user.id)}
        uihole._stream_writer = Mock()
        uihole.action = 'user-authenticate'

        await uihole.client_connected()

        self.assertTrue(hole.HoleHandler.user_authenticate.called)


@patch.object(repository, 'repo_added', AsyncMagicMock())
@patch.object(repository, 'ui_notifications', AsyncMagicMock())
@patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
@patch.object(repository.utils, 'log', Mock())
class HoleHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        hole.UIHole._shutting_down = False

        self.protocol = MagicMock()
        self.send_response = MagicMock()
        self.protocol.send_response = asyncio.coroutine(
            lambda *a, **kw: self.send_response(*a, **kw))
        self.handler = hole.HoleHandler({}, 'my-action', self.protocol)

    @async_test
    async def tearDown(self):
        await hole.Slave.drop_collection()
        await hole.Repository.drop_collection()
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await hole.User.drop_collection()

    @async_test
    async def test_handle(self):
        self.handler.action = 'my-action'
        self.handler.my_action = lambda *a, **kw: None

        await self.handler.handle()
        code = self.send_response.call_args[1]['code']

        self.assertEqual(code, 0)

    @async_test
    async def test_handle_with_coro(self):
        @asyncio.coroutine
        def my_action(*a, ** kw):
            return True

        self.handler.my_action = my_action

        await self.handler.handle()
        code = self.send_response.call_args[1]['code']

        self.assertEqual(code, 0)

    @async_test
    async def test_handle_with_not_known_action(self):
        self.handler.action = 'bad-action'

        with self.assertRaises(hole.UIFunctionNotFound):
            await self.handler.handle()

    def test_user_is_allowed_not_allowed(self):
        self.handler.protocol.user.allowed_actions = []
        self.handler.protocol.user.is_superuser = False
        is_allowed = self.handler._user_is_allowed('some-thing')
        self.assertFalse(is_allowed)

    def test_user_is_allowed_superuser(self):
        self.handler.protocol.user.is_superuser = True
        is_allowed = self.handler._user_is_allowed('some-thing')
        self.assertTrue(is_allowed)

    @async_test
    async def test_user_add_not_enough_perms(self):
        self.handler.protocol.user.allowed_actions = []
        self.handler.protocol.user.is_superuser = False
        with self.assertRaises(hole.NotEnoughPerms):
            await self.handler.user_add('a@a.com', 'password',
                                        ['repo_add', 'slave_add'])

    @async_test
    async def test_user_add(self):
        response = await self.handler.user_add('a@a.com', 'password',
                                               ['repo_add', 'slave_add'])
        self.assertTrue(response['user-add']['id'])

    @async_test
    async def test_user_remove_not_enough_perms(self):
        response = await self.handler.user_add('a@a.com', 'password',
                                               ['repo_add', 'slave_add'])
        self.handler.protocol.user.allowed_actions = []
        self.handler.protocol.user.is_superuser = False
        uid = response['user-add']['id']
        with self.assertRaises(hole.NotEnoughPerms):
            await self.handler.user_remove(id=uid)

    @async_test
    async def test_user_remove(self):
        response = await self.handler.user_add('a@a.com', 'password',
                                               ['repo_add', 'slave_add'])
        user_id = response['user-add']['id']
        response = await self.handler.user_remove(id=user_id)
        self.assertEqual(response['user-remove'], 'ok')

    @async_test
    async def test_user_remove_himself(self):
        response = await self.handler.user_add('a@a.com', 'password',
                                               ['repo_add', 'slave_add'])
        user_id = response['user-add']['id']
        user = await hole.User.objects.get(id=user_id)
        self.handler.protocol.user = user
        response = await self.handler.user_remove(id=user_id)
        self.assertEqual(response['user-remove'], 'ok')

    @async_test
    async def test_user_authenticate(self):
        await self._create_test_data_owner(passwd=True)
        response = await self.handler.user_authenticate(
            'asdf@adsf.con', 'asdf')
        user_id = response['user-authenticate']['id']
        self.assertEqual(str(self.owner.id), user_id)

    @patch.object(hole.User, 'authenticate', AsyncMagicMock(
        return_value=Mock()))
    @async_test
    async def test_user_change_password(self):
        user = hole.User.authenticate.return_value
        user.save = AsyncMagicMock()
        await self.handler.user_change_password('some@one.net', 'old-password',
                                                'new-password')
        self.assertTrue(user.set_password.called)

    @patch.object(hole, 'User', AsyncMagicMock())
    @patch.object(hole, 'ResetUserPasswordToken', AsyncMagicMock())
    @async_test
    async def test_user_send_reset_password_email(self):
        email = 'a@a.com'
        subject = 'email subject'
        message = 'email message'
        await self.handler.user_send_reset_password_email(email, subject,
                                                          message)
        obj = hole.ResetUserPasswordToken.create.return_value
        self.assertTrue(obj.send_reset_email.called_with('subject, message'))

    @patch.object(hole.ResetUserPasswordToken, 'objects', AsyncMagicMock())
    @async_test
    async def test_user_change_password_with_token(self):
        user = hole.User()
        user.save = AsyncMagicMock()
        user.set_password = Mock()
        obj = hole.ResetUserPasswordToken(user=user)
        hole.ResetUserPasswordToken.objects.get.return_value = obj

        await self.handler.user_change_password_with_token(
            'some-token', '123')

        self.assertTrue(user.set_password.called)
        self.assertTrue(user.save.called)

    @async_test
    async def test_user_get(self):
        await self._create_test_data_owner()
        r = await self.handler.user_get(id=str(self.owner.id))
        user = r['user-get']
        self.assertEqual(user['id'], str(self.owner.id))

    @async_test
    async def test_user_exists(self):
        r = await self.handler.user_exists(username='bla')
        exists = r['user-exists']
        self.assertFalse(exists)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_add_not_enough_perms(self):
        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        self.handler.protocol.user.allowed_actions = []
        self.handler.protocol.user.is_superuser = False
        with self.assertRaises(hole.NotEnoughPerms):
            await self.handler.repo_add(name, url, 'some-owner-id',
                                        update_seconds, vcs_type,
                                        slaves)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_add(self):
        await self._create_test_data_slave()

        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        repo = await self.handler.repo_add(name, url, self.owner.id,
                                           update_seconds, vcs_type,
                                           slaves)

        self.assertTrue(repo['repo-add']['id'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_add_parallel_builds(self):
        await self._create_test_data_slave()

        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        repo = await self.handler.repo_add(name, url, self.owner.id,
                                           update_seconds, vcs_type,
                                           slaves, parallel_builds=1)

        self.assertEqual(repo['repo-add']['parallel_builds'], 1)

    def test_get_kw_for_name_or_id_name(self):
        name_or_id = 'some-name'
        expected = {'full_name': 'some-name'}
        returned = self.handler._get_kw_for_name_or_id(name_or_id)
        self.assertEqual(returned, expected)

    def test_get_kw_for_name_or_id_id(self):
        name_or_id = str(ObjectId())
        expected = {'id': name_or_id}
        returned = self.handler._get_kw_for_name_or_id(name_or_id)
        self.assertEqual(returned, expected)

    @async_test
    async def test_get_owner_user_does_not_exist(self):
        with self.assertRaises(hole.OwnerDoesNotExist):
            handler = hole.HoleHandler({}, 'action', MagicMock())
            await handler._get_owner(ObjectId())

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_get_with_repo_name(self):
        await self._create_test_data()
        await asyncio.sleep(0)
        repo_name = 'asdf/reponame'
        action = 'repo-get'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        repo = (await handler.repo_get(repo_name_or_id=repo_name))['repo-get']

        self.assertEqual(repo['name'], 'reponame')
        self.assertTrue(repo['id'])
        self.assertIn('status', repo.keys())

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_get_with_repo_url(self):
        await self._create_test_data()
        await asyncio.sleep(0.1)
        repo_url = 'git@somewhere.com'
        action = 'repo-get'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        repo = (await handler.repo_get(repo_url=repo_url))['repo-get']

        self.assertEqual(repo['url'], repo_url)

    @async_test
    async def test_repo_get_without_params(self):
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())

        with self.assertRaises(TypeError):
            await handler.repo_get()

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'shutil', Mock())
    @async_test
    async def test_repo_remove(self):
        await self._create_test_data()
        action = 'repo-remove'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        await handler.repo_remove(repo_name_or_id='asdf/reponame')
        allrepos = [r.name for r in (
            await hole.Repository.objects.to_list())]
        self.assertEqual((await hole.Repository.objects.count()),
                         1, allrepos)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_list(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-list', protocol)
        repo_list = (await handler.repo_list())['repo-list']

        self.assertEqual(len(repo_list), 2)
        self.assertIn('status', repo_list[0].keys())

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_update(self):
        await self._create_test_data()

        data = {'url': 'git@somewhere.com',
                'update_seconds': 60}
        action = 'repo-update'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, action, protocol)
        await handler.repo_update(repo_name_or_id=self.repo.id,
                                  update_seconds=60)
        repo = await hole.Repository.objects.get(name=self.repo.name)

        self.assertEqual(repo.update_seconds, 60)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_update_with_slaves(self):
        await self._create_test_data()

        data = {'url': 'git@somewhere.com',
                'update_seconds': 60}
        action = 'repo-update'
        protocol = MagicMock()
        protocol.user = self.owner

        handler = hole.HoleHandler(data, action, protocol)
        slaves = ['name']
        await handler.repo_update(repo_name_or_id=self.repo.id,
                                  update_seconds=60, slaves=slaves)
        repo = await hole.Repository.objects.get(name=self.repo.name)
        self.assertEqual(repo.update_seconds, 60)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_add_slave(self):
        await self._create_test_data()

        slave = await hole.Slave.create(name='name2',
                                        host='127.0.0.1', port=1234,
                                        owner=self.owner,
                                        token='asdf')

        repo_name = self.repo.full_name
        action = 'repo-add-slave'

        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)

        await handler.repo_add_slave(repo_name_or_id=repo_name,
                                     slave_name_or_id='asdf/name2')

        repo = await hole.Repository.objects.get(url=self.repo.url)

        self.assertEqual((await repo.slaves)[0].id, slave.id)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_remove_slave(self):
        await self._create_test_data()

        slave = await hole.Slave.create(name='name2', host='127.0.0.1',
                                        port=1234, token='123',
                                        owner=self.owner)
        await self.repo.add_slave(slave)
        protocol = MagicMock()
        protocol.user = self.owner

        handler = hole.HoleHandler({}, 'repo-remove-slave', protocol)

        await handler.repo_remove_slave(self.repo.full_name, slave.full_name)

        repo = await hole.Repository.objects.get(url=self.repo.url)

        self.assertEqual(len((await repo.slaves)), 0)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_add_branch(self):
        await self._create_test_data()
        action = 'repo-add-branch'

        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)

        await handler.repo_add_branch(repo_name_or_id=self.repo.id,
                                      branch_name='release',
                                      notify_only_latest=True)

        repo = await hole.Repository.objects.get(url=self.repo.url)

        self.assertEqual(len(repo.branches), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_remove_branch(self):
        await self._create_test_data()
        action = 'repo-add-branch'

        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)

        await handler.repo_add_branch(repo_name_or_id=self.repo.full_name,
                                      branch_name='release',
                                      notify_only_latest=True)
        repo = await hole.Repository.objects.get(url=self.repo.url)
        branch_count = len(repo.branches)
        await handler.repo_remove_branch(repo_name_or_id=self.repo.id,
                                         branch_name='release')

        await repo.reload('branches')
        self.assertEqual(len(repo.branches), branch_count - 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock(
        spec=repository.BuildManager))
    @patch.object(hole.Repository, 'add_builds_for_buildset', MagicMock(
        spec=repository.Repository.add_builds_for_buildset))
    @patch.object(hole.Repository, '_get_builders',
                  create_autospec(spec=hole.Repository._get_builders,
                                  mock_cls=AsyncMagicMock))
    @patch.object(hole.Repository, 'get_config_for', AsyncMagicMock(
        spec=hole.Repository.get_config_for))
    @async_test
    async def test_repo_start_build(self):
        await self._create_test_data()
        add_builds_for_buildset = MagicMock()
        hole.Repository.add_builds_for_buildset = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_buildset(*a, **kw))
        (await self.revision.repository).build_manager\
            .get_builders = asyncio.coroutine(lambda s, r: [self.builders[0]])
        hole.Repository._get_builders.return_value = ({
            self.slave: self.builders[0]}, 'master')
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.slaves = [self.slave]
        await self.repo.save()

        await handler.repo_start_build(self.repo.id, 'master')

        self.assertEqual(len(add_builds_for_buildset.call_args_list), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(hole.Repository, 'add_builds_for_buildset', MagicMock(
        spec=repository.Repository.add_builds_for_buildset))
    @patch.object(hole.Repository, 'get_config_for', AsyncMagicMock(
        spec=hole.Repository.get_config_for))
    @async_test
    async def test_repo_start_build_with_builder_name(self):
        add_builds_for = MagicMock()
        hole.Repository.add_builds_for_buildset = asyncio.coroutine(
            lambda *a, **kw: add_builds_for(*a, **kw))
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.slaves = [self.slave]
        await self.repo.save()
        await handler.repo_start_build(self.repo.id, 'master',
                                       builder_name='b00')

        self.assertEqual(len(add_builds_for.call_args_list), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock(
        spec=repository.BuildManager, autospec=True))
    @patch.object(repository.RepositoryRevision, 'get', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_buildset', MagicMock(
        spec=repository.Repository.add_builds_for_buildset))
    @patch.object(hole.Repository, '_get_builders',
                  create_autospec(spec=hole.Repository._get_builders,
                                  mock_cls=AsyncMagicMock))
    @patch.object(hole.Repository, 'get_config_for', AsyncMagicMock(
        spec=hole.Repository.get_config_for))
    @async_test
    async def test_repo_start_build_with_named_tree(self):
        add_builds_for_buildset = MagicMock()
        hole.Repository.add_builds_for_buildset = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_buildset(*a, **kw))

        get_mock = MagicMock()

        @asyncio.coroutine
        def get(*a, **kw):
            get_mock()
            return self.revision

        repository.RepositoryRevision.get = get
        await self._create_test_data()

        hole.Repository._get_builders.return_value = ({
            self.slave: self.builders[0]}, 'master')
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.build_manager.get_builders = create_autospec(
            spec=self.repo.build_manager.get_bulders, autospec=True,
            mock_cls=AsyncMagicMock)
        self.repo.slaves = [self.slave]
        await self.repo.save()
        await handler.repo_start_build(self.repo.full_name, 'master',
                                       named_tree='123qewad')

        self.assertTrue(get_mock.called)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock())
    @patch.object(hole.Repository, 'get_for_user', AsyncMagicMock(
        spec=hole.Repository.get_for_user))
    @async_test
    async def test_repo_cancel_build(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-cancel-build', protocol)
        await handler.repo_cancel_build('some-repo-id', 'some-build-uuid')
        repo = hole.Repository.get_for_user.return_value
        self.assertTrue(repo.cancel_build.called)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock())
    @patch.object(hole.Repository, 'get_for_user', AsyncMagicMock(
        spec=hole.Repository.get_for_user))
    @async_test
    async def test_repo_cancel_build_repo_id(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-cancel-build', protocol)
        await handler.repo_cancel_build(str(self.repo.id), 'some-build-uuid')
        repo = hole.Repository.get_for_user.return_value
        self.assertTrue(repo.cancel_build.called)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_enable(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-enable', protocol)
        await self.repo.disable()
        await handler.repo_enable(str(self.repo.id))
        await self.repo.reload()
        self.assertTrue(self.repo.enabled)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_disable(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-disable', protocol)
        await self.repo.enable()
        await handler.repo_disable(str(self.repo.id))
        await self.repo.reload()
        self.assertFalse(self.repo.enabled)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_add(self):
        await self._create_test_data_owner()
        data = {'host': '127.0.0.1', 'port': 1234}
        handler = hole.HoleHandler(data, 'slave-add', MagicMock())
        slave = await handler.slave_add(slave_name='slave',
                                        slave_host='locahost',
                                        slave_port=1234,
                                        owner_id=self.owner.id,
                                        slave_token='1234')
        slave = slave['slave-add']

        self.assertTrue(slave['id'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_add_not_enough_perms(self):
        await self._create_test_data_owner()
        self.handler.protocol.user.allowed_actions = []
        self.handler.protocol.user.is_superuser = False
        with self.assertRaises(hole.NotEnoughPerms):
            await self.handler.slave_add(slave_name='slave',
                                         slave_host='locahost',
                                         slave_port=1234,
                                         owner_id=self.owner.id,
                                         slave_token='1234')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_get(self):
        await self._create_test_data_slave()
        slave_name = 'asdf/name'
        self.handler.protocol.user = self.owner
        slave = (await self.handler.slave_get(
            slave_name_or_id=slave_name))['slave-get']

        self.assertEqual(slave['full_name'], slave_name)
        self.assertTrue(slave['id'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_remove(self):
        await self._create_test_data_slave()
        data = {'host': '127.0.0.1', 'port': 7777}
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, 'slave-remove', protocol)
        await handler.slave_remove(slave_name_or_id='asdf/name')
        await asyncio.sleep(0.1)
        self.assertEqual((await hole.Slave.objects.count()), 0)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_list(self):
        await self._create_test_data_slave()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'slave-list', protocol)
        slaves = (await handler.slave_list())['slave-list']

        self.assertEqual(len(slaves), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_update(self):
        await self._create_test_data_slave()

        data = {'host': '10.0.0.1', 'slave_name': self.slave.name}
        action = 'slave-update'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, action, protocol)
        await handler.slave_update(slave_name_or_id=self.slave.id,
                                   host='10.0.0.1')
        slave = await hole.Slave.get(id=self.slave.id)
        self.assertEqual(slave.host, '10.0.0.1')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_buildset_list(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'buildset-list', protocol)
        buildsets = await handler.buildset_list(self.repo.full_name)
        buildsets = buildsets['buildset-list']

        self.assertEqual(len(buildsets), 3)
        self.assertEqual(len(buildsets[0]['builds']), 5)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_buildset_list_summary(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'buildset-list', protocol)
        buildsets = await handler.buildset_list(self.repo.full_name,
                                                summary=True)
        buildsets = buildsets['buildset-list']

        self.assertEqual(len(buildsets), 3)
        self.assertEqual(len(buildsets[0]['builds']), 0)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_buildset_list_without_repo_name(self):

        await self._create_test_data()
        handler = hole.HoleHandler({}, 'buildset-list', MagicMock())

        builders = await handler.buildset_list()
        builders = {'buildset-list': 'asd'}
        builders = builders['buildset-list']
        self.assertEqual(len(builders), 3)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_buildset_get_no_perms(self):
        await self._create_test_data()
        buildset = self.buildset
        user = MagicMock()
        user.id = 'some-id'
        user.is_superuser = False
        self.protocol.user = user
        with self.assertRaises(hole.NotEnoughPerms):
            await self.handler.buildset_get(buildset.id)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_buildset_get(self):
        await self._create_test_data()
        buildset = self.buildset
        user = MagicMock()
        user.id = 'some-id'
        self.protocol.user = user
        b = (await self.handler.buildset_get(buildset.id))['buildset-get']
        self.assertTrue(b['id'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_builder_list(self):
        await self._create_test_data()
        handler = hole.HoleHandler({}, 'builder-list', MagicMock())

        builders = (await handler.builder_list(
            id__in=[self.builders[0].id]))['builder-list']
        self.assertEqual(builders[0]['id'], str(self.builders[0].id))

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_build_get_no_perms(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        user = MagicMock()
        user.id = 'some-id'
        user.is_superuser = False
        self.protocol.user = user
        with self.assertRaises(hole.NotEnoughPerms):
            await self.handler.build_get(build_inst.uuid)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_build_get(self):
        await self._create_test_data()
        build_inst = self.buildset.builds[0]
        step = build.BuildStep(command='ls', status='success',
                               output='nada.txt\n',
                               name='list-files')
        build_inst.steps.append(step)
        await build_inst.update()
        build_r = (await self.handler.build_get(
            build_inst.uuid))['build-get']
        self.assertTrue(build_r['output'])
        self.assertTrue(build_r['repository']['name'])
        self.assertTrue(build_r['builder']['name'])
        self.assertTrue(build_r['commit'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_builder_show(self):
        await self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, action, protocol)
        builder = await handler.builder_show(repo_name_or_id=self.repo.id,
                                             builder_name='b01')
        builder = builder['builder-show']

        self.assertEqual(len(builder['buildsets']), 1)
        self.assertEqual(len(builder['buildsets'][0]['builds']), 3)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_builder_show_with_skip_and_offset(self):
        await self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, action, protocol)
        builder = await handler.builder_show(
            repo_name_or_id=self.repo.full_name,
            builder_name='b01',
            skip=1, offset=1)
        builder = builder['builder-show']

        self.assertEqual(len(builder['buildsets']), 0)

    def test_get_method_signature(self):

        def target(a, b='bla', c=None):
            pass

        expected = {'doc': '',
                    'parameters': [{'name': 'a', 'required': True},
                                   {'name': 'b', 'required': False,
                                    'default': 'bla'},
                                   {'name': 'c', 'required': False,
                                    'default': None}]}

        handler = hole.HoleHandler({}, 'action', MagicMock())
        returned = handler._get_method_signature(target)

        self.assertEqual(returned, expected, returned)

    def test_list_funcs(self):
        handler = hole.HoleHandler({}, 'action', MagicMock())
        funcs = handler.list_funcs()['list-funcs']

        keys = sorted([k.replace('_', '-') for k
                       in handler._get_action_methods().keys()])
        funcs = sorted(list(funcs.keys()))
        self.assertEqual(funcs, keys)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_repo_dict(self):
        await self._create_test_data()
        self.repo.slaves = [self.slave]

        handler = hole.HoleHandler({}, 'action', MagicMock())
        repo_dict = await handler._get_repo_dict(self.repo)

        self.assertIn('id', repo_dict)
        self.assertIn('slaves', repo_dict)
        self.assertTrue('status', repo_dict)
        self.assertTrue(repo_dict['slaves'][0]['name'])
        self.assertIn('parallel_builds', repo_dict.keys())
        self.assertTrue(repo_dict['last_buildset'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_slave_dict(self):
        await self._create_test_data_slave()

        handler = hole.HoleHandler({}, 'action', MagicMock())
        slave_dict = handler._get_slave_dict(self.slave)

        self.assertEqual(type(slave_dict['id']), str)

    async def _create_test_data_owner(self, passwd=False):
        self.owner = hole.User(email='asdf@adsf.con',
                               allowed_actions=['add_user', 'add_repo',
                                                'add_slave', 'remove_user'])
        if passwd:
            self.owner.set_password('asdf')
        await self.owner.save()

    async def _create_test_data_slave(self):
        await self._create_test_data_owner()
        self.slave = hole.Slave(name='name', host='127.0.0.1', port=7777,
                                token='123', owner=self.owner)
        await self.slave.save()

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(repository.utils, 'log', Mock())
    async def _create_test_data(self):
        await self._create_test_data_slave()
        await self._create_test_data_owner()
        self.repo = await hole.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git')
        self.other_repo = await hole.Repository.create(
            name='other', url='git@bla.com', owner=self.owner,
            update_seconds=300, vcs_type='git')

        self.builds = []
        now = datetime.now()
        for k in range(3):
            self.revision = repository.RepositoryRevision(
                repository=self.repo,
                commit='123qewad{}'.format(k),
                branch='master',
                commit_date=now, author='zé', title='boa!')
            await self.revision.save()
            self.buildset = await build.BuildSet.create(
                repository=self.repo, revision=self.revision)
            self.buildset.status = 'warning'
            await self.buildset.save(revision=self.revision)
            builds = []
            self.builders = []
            for i in range(3):
                builder = build.Builder(name='b{}{}'.format(i, k),
                                        repository=self.repo)
                await builder.save()
                if i == 0:
                    r = 3
                else:
                    r = 1

                for j in range(r):
                    build_inst = build.Build(repository=self.repo,
                                             slave=self.slave,
                                             branch='master',
                                             named_tree='v0.{}'.format(j),
                                             started=datetime.now(),
                                             finished=datetime.now(),
                                             builder=builder, status='success')
                    builds.append(build_inst)
                    self.builders.append(builder)

            self.buildset.builds = builds
            await self.buildset.save()

        await asyncio.sleep(0)


@patch.object(repository, 'ui_notifications', AsyncMagicMock())
@patch.object(repository, 'repo_added', AsyncMagicMock())
@patch.object(repository, 'repo_status_changed', AsyncMagicMock())
@patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
@patch.object(hole.UIStreamHandler, 'log', Mock())
class UIStreamHandlerTest(TestCase):

    @async_test
    async def setUp(self):
        super().setUp()
        protocol = MagicMock()
        self.handler = hole.UIStreamHandler(protocol)
        self.owner = hole.User(email='aasdf@a.com', password='asdf')
        await self.owner.save()
        self.handler.protocol.user = self.owner

    @async_test
    async def tearDown(self):
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await slave.Slave.drop_collection()
        await repository.Repository.drop_collection()
        await hole.User.drop_collection()

    @patch.object(hole.UIStreamHandler, '_connect_repo', MagicMock())
    @patch.object(hole.Repository, 'get_for_user', AsyncMagicMock(
        spec=hole.Repository.get_for_user, side_effect=hole.NotEnoughPerms))
    @async_test
    async def test_check_repo_added_no_perms(self):
        msg = AsyncMagicMock()
        msg.body = {'id': 'some-id'}
        await self.handler.check_repo_added(msg)
        self.assertFalse(self.handler._connect_repo.called)

    @patch.object(hole.UIStreamHandler, '_connect_repo', MagicMock())
    @patch.object(hole.Repository, 'get_for_user', AsyncMagicMock(
        spec=hole.Repository.get_for_user))
    @async_test
    async def test_check_repo_added(self):
        msg = AsyncMagicMock()
        msg.body = {'id': 'some-id'}
        self.handler.protocol.send_response = AsyncMagicMock()
        await self.handler.check_repo_added(msg)
        self.assertTrue(self.handler._connect_repo.called)

    @patch.object(hole, 'step_started', Mock())
    @patch.object(hole, 'step_finished', Mock())
    @patch.object(hole, 'build_started', Mock())
    @patch.object(hole, 'build_finished', Mock())
    @patch.object(hole, 'ui_notifications', AsyncMagicMock())
    @patch.object(hole, 'build_added', Mock())
    @patch.object(hole, 'step_output_arrived', Mock())
    @patch.object(hole, 'buildset_started', Mock())
    @patch.object(hole, 'buildset_finished', Mock())
    def test_disconnectfromsignals(self):

        self.handler._disconnectfromsignals()
        self.assertTrue(all([hole.step_started.disconnect.called,
                             hole.step_finished.disconnect.called,
                             hole.build_started.disconnect.called,
                             hole.build_finished.disconnect.called,
                             hole.build_added.disconnect.called,
                             hole.buildset_started.disconnect.called,
                             hole.buildset_finished.disconnect.called,
                             hole.step_output_arrived.disconnect.called]))
        self.assertTrue(hole.ui_notifications.publish.called)
        kw = hole.ui_notifications.publish.call_args[1]
        self.assertIn('routing_key', kw)

    @patch.object(hole, 'step_started', Mock())
    @patch.object(hole, 'step_finished', Mock())
    @patch.object(hole, 'build_started', Mock())
    @patch.object(hole, 'build_finished', Mock())
    @patch.object(hole, 'build_added', Mock())
    @patch.object(hole, 'step_output_arrived', Mock())
    @patch.object(hole, 'buildset_started', Mock())
    @patch.object(hole, 'buildset_finished', Mock())
    @async_test
    async def test_connect2signals(self):

        repo = hole.Repository(url='https://bla.com/git', vcs_type='git',
                               owner=self.owner, name='my-repo')
        await repo.save()
        self.handler._handle_repo_status_changed = AsyncMagicMock()
        self.handler._handle_repo_added = AsyncMagicMock()
        self.handler._handle_ui_notifications = AsyncMagicMock(
            spec=self.handler._handle_ui_notifications)
        event_types = ['step_started', 'step_finished', 'build_started',
                       'build_finished', 'build_cancelled',
                       'step_output_arrived', 'build_added',
                       'buildset_started', 'buildset_finished']

        await self.handler._connect2signals(event_types)
        self.assertTrue(all([hole.step_started.connect.called,
                             hole.step_finished.connect.called,
                             hole.build_started.connect.called,
                             hole.build_finished.connect.called,
                             hole.build_added.connect.called,
                             hole.buildset_started.connect.called,
                             hole.buildset_finished.connect.called,
                             hole.step_output_arrived.connect.called]))

    @async_test
    async def test_connect2signals_repo_added(self):
        self.handler._handle_ui_notifications = AsyncMagicMock(
            spec=self.handler._handle_ui_notifications)

        event_types = ['repo_added']
        await self.handler._connect2signals(event_types)
        self.assertTrue(self.handler._handle_ui_notifications.called)

    @patch.object(hole, 'ui_notifications', AsyncMagicMock())
    @async_test
    async def test_handle_ui_notifications(self):
        consumer = hole.ui_notifications.consume.return_value
        msg0 = AsyncMagicMock()
        msg0.body = {'msg_type': 'repo_added'}
        msg1 = AsyncMagicMock()
        msg1.body = {'msg_type': 'stop_consumption'}
        consumer.fetch_message.side_effect = [msg0, msg1]
        self.handler._handle_ui_message = AsyncMagicMock()
        await self.handler._handle_ui_notifications()
        self.assertTrue(self.handler._handle_ui_message.called)

    @async_test
    async def test_handle_ui_message_repo_added(self):
        msg = AsyncMagicMock()
        msg.body = {'msg_type': 'repo_added'}
        self.handler.check_repo_added = AsyncMagicMock()
        await self.handler._handle_ui_message(msg)
        self.assertTrue(self.handler.check_repo_added.called)

    @async_test
    async def test_handle_ui_message_repo_status_changed(self):
        msg = AsyncMagicMock()
        msg.body = {'msg_type': 'repo_status_changed'}
        self.handler.send_repo_status_info = AsyncMagicMock()
        await self.handler._handle_ui_message(msg)
        self.assertTrue(self.handler.send_repo_status_info.called)

    @async_test
    async def test_handle_ui_message_unknown(self):
        msg = AsyncMagicMock()
        msg.body = {'msg_type': 'something'}
        self.handler.check_repo_added = AsyncMagicMock()
        self.handler.log = Mock()
        await self.handler._handle_ui_message(msg)
        self.assertTrue(self.handler.log.called)

    @async_test
    async def test_step_started(self):
        send_info = MagicMock()
        self.handler.send_info = asyncio.coroutine(
            lambda *a, **kw: send_info(*a, **kw))
        await self.handler.step_started(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'step_started')

    @async_test
    async def test_step_finished(self):
        send_info = MagicMock()
        self.handler.send_info = asyncio.coroutine(
            lambda *a, **kw: send_info(*a, **kw))
        await self.handler.step_finished(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'step_finished')

    @async_test
    async def test_build_preparing(self):
        send_info = MagicMock()
        self.handler.send_info = asyncio.coroutine(
            lambda *a, **kw: send_info(*a, **kw))
        await self.handler.build_preparing(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'build_preparing')

    @async_test
    async def test_build_started(self):
        send_info = MagicMock()
        self.handler.send_info = asyncio.coroutine(
            lambda *a, **kw: send_info(*a, **kw))
        await self.handler.build_started(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'build_started')

    @async_test
    async def test_build_finished(self):
        send_info = MagicMock()
        self.handler.send_info = asyncio.coroutine(
            lambda *a, **kw: send_info(*a, **kw))
        await self.handler.build_finished(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'build_finished')

    @async_test
    async def test_buildset_started(self):
        self.handler.send_buildset_info = AsyncMagicMock(
            spec=self.handler.send_buildset_info)

        await self.handler.buildset_started(Mock(), buildset=Mock())

        called = self.handler.send_buildset_info.call_args[0][0]
        self.assertEqual(called, 'buildset_started')

    @async_test
    async def test_buildset_finished(self):
        self.handler.send_buildset_info = AsyncMagicMock(
            spec=self.handler.send_buildset_info)

        await self.handler.buildset_finished(Mock(), buildset=Mock())

        called = self.handler.send_buildset_info.call_args[0][0]
        self.assertEqual(called, 'buildset_finished')

    @async_test
    async def test_buildset_added(self):
        self.handler.send_buildset_info = AsyncMagicMock(
            spec=self.handler.send_buildset_info)

        await self.handler.buildset_added(Mock(), buildset=Mock())

        called = self.handler.send_buildset_info.call_args[0][0]
        self.assertEqual(called, 'buildset_added')

    @async_test
    async def test_build_added(self):
        send_info = MagicMock()
        self.handler.send_info = asyncio.coroutine(
            lambda *a, **kw: send_info(*a, **kw))
        await self.handler.build_added(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'build_added')

    @async_test
    async def test_build_cancelled_fn(self):
        send_info = AsyncMagicMock()
        self.handler.send_info = send_info
        await self.handler.build_cancelled(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'build_cancelled')

    @async_test
    async def test_handle(self):
        self.handler._connect2signals = AsyncMagicMock(
            spec=hole.UIStreamHandler._connect2signals)
        send_response = MagicMock()
        self.handler.protocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))

        await self.handler.handle()

        self.assertTrue(self.handler._connect2signals.called)
        self.assertTrue(send_response.called)

    @async_test
    async def test_send_buildset_info(self):
        repo = await repository.Repository.create(name='name',
                                                  url='git@git.nada',
                                                  owner=self.owner,
                                                  update_seconds=300,
                                                  vcs_type='git')
        builder = build.Builder(name='bla')
        b = build.Build()
        b.builder = builder
        buildset = build.BuildSet(repository=repo, started=datetime.now(),
                                  commit_date=datetime.now(), builds=[b])
        event_type = 'buildset_started'
        self.handler.send_response = AsyncMagicMock(
            spec=self.handler.send_response)

        await self.handler.send_buildset_info(event_type, buildset)
        buildset_dict = self.handler.send_response.call_args[1]['body']
        build_dict = buildset_dict['builds'][0]
        self.assertTrue(build_dict['builder']['name'])

        self.assertTrue(self.handler.send_response.called)
        # bdict = self.handler.send_response.call_args[1]['body']

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', Mock())
    @async_test
    async def test_send_info_step(self):
        testrepo = await repository.Repository.create(name='name',
                                                      url='git@git.nada',
                                                      owner=self.owner,
                                                      update_seconds=300,
                                                      vcs_type='git')
        testslave = await slave.Slave.create(name='name',
                                             host='localhost',
                                             owner=self.owner,
                                             port=1234, token='123')

        testbuilder = await build.Builder.create(name='b1',
                                                      repository=testrepo)
        testbuild = build.Build(repository=testrepo, slave=testslave,
                                branch='master', named_tree='master',
                                builder=testbuilder, status='running')

        teststep = build.BuildStep(name='s1', command='ls', status='running',
                                   output='')
        testbuild.steps.append(teststep)

        rev = repository.RepositoryRevision(repository=testrepo,
                                            commit='açsdlfj',
                                            branch='master',
                                            author='eu',
                                            title='some',
                                            commit_date=datetime.now())
        await rev.save()
        buildset = await build.BuildSet.create(testrepo, rev)
        buildset.builds.append(testbuild)
        await buildset.save()

        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.send_response = sr

        await self.handler.send_info('step_started',
                                     sender=testrepo.id,
                                     build=testbuild, step=teststep)

        await asyncio.sleep(0)
        self.assertEqual(self.CODE, 0)
        self.assertIn('build', self.BODY.keys())

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', Mock())
    @async_test
    async def test_send_info_build(self):
        testrepo = await repository.Repository.create(name='name',
                                                      url='git@git.nada',
                                                      owner=self.owner,
                                                      update_seconds=300,
                                                      vcs_type='git')
        testslave = await slave.Slave.create(name='name',
                                             host='localhost',
                                             port=1234,
                                             owner=self.owner,
                                             token='123')
        testbuilder = await build.Builder.create(name='b1',
                                                 repository=testrepo)
        testbuild = build.Build(repository=testrepo, slave=testslave,
                                branch='master', named_tree='master',
                                builder=testbuilder, status='running')
        rev = repository.RepositoryRevision(repository=testrepo,
                                            commit='açsdlfj',
                                            branch='master',
                                            author='eu',
                                            title='some',
                                            commit_date=datetime.now())
        await rev.save()
        buildset = await build.BuildSet.create(testrepo, rev)
        buildset.builds.append(testbuild)
        await buildset.save()

        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.send_response = sr
        await self.handler.send_info('step-started', sender=testrepo.id,
                                     build=testbuild)
        await asyncio.sleep(0)
        self.assertEqual(self.CODE, 0)
        self.assertIn('steps', self.BODY.keys())
        self.assertIn('buildset', self.BODY.keys())

        self.assertIsInstance(self.BODY['slave']['id'], str)
        self.assertIsInstance(self.BODY['repository']['id'], str)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @async_test
    async def test_send_repo_status_info(self):
        testslave = await slave.Slave.create(name='name',
                                             host='localhost',
                                             port=1234,
                                             token='123',
                                             owner=self.owner)

        testrepo = await repository.Repository.create(name='name',
                                                      url='git@git.nada',
                                                      owner=self.owner,
                                                      update_seconds=300,
                                                      vcs_type='git',
                                                      slaves=[testslave])
        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.send_response = sr
        msg = AsyncMagicMock()
        msg.body = dict(repository_id=str(testrepo.id),
                        new_status='fail',
                        old_status='running')
        await self.handler.send_repo_status_info(msg)

        await asyncio.sleep(0)
        self.assertEqual(self.BODY['status'], 'fail')
        self.assertIsInstance(self.BODY['id'], str)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @async_test
    async def test_send_step_output_info(self):
        testslave = await slave.Slave.create(name='name',
                                             host='localhost',
                                             port=1234,
                                             owner=self.owner,
                                             token='123')

        testrepo = await repository.Repository.create(name='name',
                                                      url='git@git.nada',
                                                      owner=self.owner,
                                                      update_seconds=300,
                                                      vcs_type='git',
                                                      slaves=[testslave])

        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.protocol.send_response = sr

        info = {'uuid': 'some-uuid', 'output': 'bla!'}
        f = self.handler.step_output_arrived(repo=testrepo,
                                             step_info=info)
        await f

        self.assertEqual(self.BODY['uuid'], 'some-uuid')

    @async_test
    async def test_send_response(self):
        sr_mock = MagicMock()

        @asyncio.coroutine
        def sr(code, body):
            sr_mock()

        self.handler.protocol.send_response = sr
        await self.handler.send_response(code=0, body='bla')
        self.assertTrue(sr_mock.called)

    @async_test
    async def test_send_response_exception(self):

        @asyncio.coroutine
        def sr(code, body):
            raise ConnectionResetError

        self.handler.protocol.send_response = sr
        self.handler.log = MagicMock()
        self.handler.protocol._transport.close = MagicMock()
        self.handler._disconnectfromsignals = MagicMock()
        await self.handler.send_response(code=0, body='bla')
        self.assertTrue(self.handler.protocol._transport.close.called)
        self.assertTrue(self.handler._disconnectfromsignals.called)


class HoleServerTest(TestCase):

    def setUp(self):
        super().setUp()
        self.server = hole.HoleServer()

    def test_get_protocol_instance(self):
        prot = self.server.get_protocol_instance()

        self.assertEqual(hole.UIHole, type(prot))

    @patch.object(hole.asyncio, 'get_event_loop', Mock())
    @patch.object(hole, 'ensure_future', Mock())
    def test_serve(self):
        self.server.serve()

        self.assertTrue(hole.ensure_future.called)

    @patch.object(hole.ssl, 'create_default_context', MagicMock(
        spec=hole.ssl.create_default_context))
    @patch.object(hole.asyncio, 'get_event_loop', Mock())
    @patch.object(hole, 'ensure_future', Mock())
    def test_serve_ssl(self):
        loop = MagicMock()
        self.server.use_ssl = True
        self.server.loop = loop
        self.server.serve()
        kw = loop.create_server.call_args[1]
        ssl_context = hole.ssl.create_default_context.return_value
        self.assertTrue(ssl_context.load_cert_chain.called)
        self.assertIn('ssl', kw.keys())
        self.assertTrue(hole.ensure_future.called)

    @patch.object(hole.asyncio, 'sleep',
                  AsyncMagicMock(spec=hole.asyncio.sleep))
    @async_test
    async def test_shutdown(self):

        sleep_mock = MagicMock()

        async def sleep(t):
            sleep_mock()
            hole.Repository.remove_running_build()

        hole.asyncio.sleep = sleep
        hole.RepositoryMessageConsumer()
        hole.Repository.add_running_build()
        await self.server.shutdown()

        self.assertTrue(sleep_mock.called)

    def test_sync_shutdown(self):
        self.server.shutdown = AsyncMagicMock()
        self.server.sync_shutdown()
        self.assertTrue(self.server.shutdown.called)
