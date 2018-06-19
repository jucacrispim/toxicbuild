# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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
from toxicbuild.master import hole, build, repository, slave, plugins
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
        self.owner = hole.User(email='asdf@adsf.con',
                               allowed_actions=['add_user', 'add_repo',
                                                'add_slave', 'remove_user'])
        self.owner.set_password('asdf')
        await self.owner.save()
        hole.UIHole._shutting_down = False

    @async_test
    async def tearDown(self):
        await hole.Slave.drop_collection()
        await hole.Repository.drop_collection()
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await hole.User.drop_collection()

    @async_test
    async def test_handle(self):
        protocol = MagicMock()
        send_response = MagicMock()
        protocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        handler = hole.HoleHandler({}, 'my-action', protocol)
        handler.my_action = lambda *a, **kw: None

        await handler.handle()
        code = send_response.call_args[1]['code']

        self.assertEqual(code, 0)

    @async_test
    async def test_handle_with_coro(self):
        protocol = MagicMock()
        send_response = MagicMock()
        protocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        handler = hole.HoleHandler({}, 'my-action', protocol)

        @asyncio.coroutine
        def my_action(*a, ** kw):
            return True

        handler.my_action = my_action

        await handler.handle()
        code = send_response.call_args[1]['code']

        self.assertEqual(code, 0)

    @async_test
    async def test_handle_with_not_known_action(self):
        handler = hole.HoleHandler({}, 'action', MagicMock())

        with self.assertRaises(hole.UIFunctionNotFound):
            await handler.handle()

    def test_user_is_allowed_not_allowed(self):
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        is_allowed = handler._user_is_allowed('some-thing')
        self.assertFalse(is_allowed)

    def test_user_is_allowed_superuser(self):
        protocol = MagicMock()
        self.owner.is_superuser = True
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        is_allowed = handler._user_is_allowed('some-thing')
        self.assertTrue(is_allowed)

    @async_test
    async def test_user_add_not_enough_perms(self):
        protocol = MagicMock()
        self.owner.allowed_actions = []
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        with self.assertRaises(hole.NotEnoughPerms):
            await handler.user_add('a@a.com', 'password',
                                   ['repo_add', 'slave_add'])

    @async_test
    async def test_user_add(self):
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        response = await handler.user_add('a@a.com', 'password',
                                          ['repo_add', 'slave_add'])
        self.assertTrue(response['user-add']['id'])

    @async_test
    async def test_user_remove_not_enough_perms(self):
        protocol = MagicMock()
        self.owner.allowed_actions = []
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        with self.assertRaises(hole.NotEnoughPerms):
            await handler.user_remove(id='bla')

    @async_test
    async def test_user_remove(self):
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        response = await handler.user_add('a@a.com', 'password',
                                          ['repo_add', 'slave_add'])
        user_id = response['user-add']['id']
        response = await handler.user_remove(id=user_id)
        self.assertEqual(response['user-remove'], 'ok')

    @async_test
    async def test_user_authenticate(self):
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'action', protocol)
        response = await handler.user_authenticate('asdf@adsf.con', 'asdf')
        user_id = response['user-authenticate']['id']
        self.assertEqual(str(self.owner.id), user_id)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_add_not_enough_perms(self):
        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        action = 'repo-add'
        protocol = MagicMock()
        self.owner.allowed_actions = []
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)

        with self.assertRaises(hole.NotEnoughPerms):
            await handler.repo_add(name, url, self.owner.id,
                                   update_seconds, vcs_type,
                                   slaves)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_add(self):
        await self._create_test_data()

        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        action = 'repo-add'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)

        repo = await handler.repo_add(name, url, self.owner.id,
                                      update_seconds, vcs_type,
                                      slaves)

        self.assertTrue(repo['repo-add']['id'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_add_parallel_builds(self):
        await self._create_test_data()

        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        action = 'repo-add'
        handler = hole.HoleHandler({}, action, MagicMock())

        repo = await handler.repo_add(name, url, self.owner.id,
                                      update_seconds, vcs_type,
                                      slaves, parallel_builds=1)

        self.assertEqual(repo['repo-add']['parallel_builds'], 1)

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
        repo_name = 'reponame'
        action = 'repo-get'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        repo = (await handler.repo_get(repo_name=repo_name))['repo-get']

        self.assertEqual(repo['name'], repo_name)
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
        await handler.repo_remove(repo_name='reponame')
        allrepos = [r.name for r in (
            await hole.Repository.objects.to_list())]
        self.assertEqual((await hole.Repository.objects.count()),
                         1, allrepos)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_repo_enable_plugin(self):

        class TestPlugin(plugins.MasterPlugin):
            name = 'test-hole-plugin'
            type = 'test'

            @asyncio.coroutine
            def run(self, sender):
                pass

        await self._create_test_data()
        action = 'repo-enable-plugin'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        await handler.repo_enable_plugin(self.repo.name,
                                         'test-hole-plugin')
        repo = await hole.Repository.objects.get(id=self.repo.id)
        self.assertEqual(len(repo.plugins), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @async_test
    async def test_repo_disable_plugin(self):

        class TestPlugin(plugins.MasterPlugin):
            name = 'test-hole-plugin'
            type = 'test'

            @asyncio.coroutine
            def run(self, sender):
                pass

        await self._create_test_data()
        action = 'repo-enable-plugin'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        await handler.repo_enable_plugin(self.repo.name,
                                         'test-hole-plugin')
        kw = {'name': 'test-hole-plugin'}
        await handler.repo_disable_plugin(self.repo.name, **kw)
        repo = await hole.Repository.objects.get(id=self.repo.id)
        self.assertEqual(len(repo.plugins), 0)

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
        await handler.repo_update(repo_name=self.repo.name,
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
        await handler.repo_update(repo_name=self.repo.name,
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

        repo_name = self.repo.name
        action = 'repo-add-slave'

        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)

        await handler.repo_add_slave(repo_name=repo_name,
                                     slave_name='name2')

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

        await handler.repo_remove_slave(self.repo.name, slave.name)

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

        await handler.repo_add_branch(repo_name=self.repo.name,
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

        await handler.repo_add_branch(repo_name=self.repo.name,
                                      branch_name='release',
                                      notify_only_latest=True)
        repo = await hole.Repository.objects.get(url=self.repo.url)
        branch_count = len(repo.branches)
        await handler.repo_remove_branch(repo_name=self.repo.name,
                                         branch_name='release')

        await repo.reload('branches')
        self.assertEqual(len(repo.branches), branch_count - 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock(
        spec=repository.BuildManager))
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @async_test
    async def test_repo_start_build(self):
        await self._create_test_data()
        add_builds_for_slave = MagicMock()
        hole.Repository.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))
        (await self.revision.repository).build_manager\
            .get_builders = asyncio.coroutine(lambda s, r: [self.builders[0]])
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.slaves = [self.slave]
        await self.repo.save()

        await handler.repo_start_build(self.repo.name, 'master')

        self.assertEqual(len(add_builds_for_slave.call_args_list), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @async_test
    async def test_repo_start_build_with_builder_name(self):
        add_builds_for_slave = MagicMock()
        hole.Repository.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.slaves = [self.slave]
        await self.repo.save()
        await handler.repo_start_build(self.repo.name, 'master',
                                       builder_name='b00')

        self.assertEqual(len(add_builds_for_slave.call_args_list), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock(
        spec=repository.BuildManager, autospec=True))
    @patch.object(repository.RepositoryRevision, 'get', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @async_test
    async def test_repo_start_build_with_named_tree(self):
        add_builds_for_slave = MagicMock()
        hole.Repository.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))

        get_mock = MagicMock()

        @asyncio.coroutine
        def get(*a, **kw):
            get_mock()
            return self.revision

        repository.RepositoryRevision.get = get
        await self._create_test_data()

        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.build_manager.get_builders = create_autospec(
            spec=self.repo.build_manager.get_bulders, autospec=True,
            mock_cls=AsyncMagicMock)
        self.repo.slaves = [self.slave]
        await self.repo.save()
        await handler.repo_start_build(self.repo.name, 'master',
                                       named_tree='123qewad')

        self.assertTrue(get_mock.called)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository, 'BuildManager', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @async_test
    async def test_repo_start_build_with_slave(self):
        await self._create_test_data()
        add_builds_for_slave = MagicMock()
        hole.Repository.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))

        hole.HoleHandler._get_builders = asyncio.coroutine(
            lambda repo, s, r, builders=None: {self.slave: self.builders[0]})
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'repo-start-build', protocol)
        self.repo.slaves = [self.slave]
        await self.repo.save()

        self.repo.build_manager.get_builders = create_autospec(
            spec=self.repo.build_manager.get_bulders, autospec=True,
            mock_cls=AsyncMagicMock)

        await handler.repo_start_build(self.repo.name, 'master',
                                       slaves=['name'])

        self.assertEqual(len(add_builds_for_slave.call_args_list), 1)

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
    @async_test
    async def test_slave_add(self):
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
        data = {'host': '127.0.0.1', 'port': 1234}
        protocol = MagicMock()
        self.owner.allowed_actions = []
        protocol.user = self.owner
        handler = hole.HoleHandler(data, 'slave-add', protocol)
        with self.assertRaises(hole.NotEnoughPerms):
            await handler.slave_add(slave_name='slave',
                                    slave_host='locahost',
                                    slave_port=1234,
                                    owner_id=self.owner.id,
                                    slave_token='1234')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_get(self):
        await self._create_test_data()
        slave_name = 'name'
        action = 'slave-get'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, action, protocol)
        slave = (await handler.slave_get(
            slave_name=slave_name))['slave-get']

        self.assertEqual(slave['name'], slave_name)
        self.assertTrue(slave['id'])

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_remove(self):
        await self._create_test_data()
        data = {'host': '127.0.0.1', 'port': 7777}
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, 'slave-remove', protocol)
        await handler.slave_remove(slave_name='name')
        await asyncio.sleep(0.1)
        self.assertEqual((await hole.Slave.objects.count()), 0)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_list(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'slave-list', protocol)
        slaves = (await handler.slave_list())['slave-list']

        self.assertEqual(len(slaves), 1)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_slave_update(self):
        await self._create_test_data()

        data = {'host': '10.0.0.1', 'slave_name': self.slave.name}
        action = 'slave-update'
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler(data, action, protocol)
        await handler.slave_update(slave_name=self.slave.name,
                                   host='10.0.0.1')
        slave = await hole.Slave.get(name=self.slave.name)
        self.assertEqual(slave.host, '10.0.0.1')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_buildset_list(self):
        await self._create_test_data()
        protocol = MagicMock()
        protocol.user = self.owner
        handler = hole.HoleHandler({}, 'buildset-list', protocol)
        buildsets = await handler.buildset_list(self.repo.name)
        buildsets = buildsets['buildset-list']

        self.assertEqual(len(buildsets), 3)
        self.assertEqual(len(buildsets[0]['builds']), 5)

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
    async def test_builder_list(self):
        await self._create_test_data()
        handler = hole.HoleHandler({}, 'builder-list', MagicMock())

        builders = (await handler.builder_list(
            id__in=[self.builders[0].id]))['builder-list']
        self.assertEqual(builders[0]['id'], str(self.builders[0].id))

    def test_plugins_list(self):
        handler = hole.HoleHandler({}, 'plugin-list', MagicMock())
        plugins_count = len(hole.MasterPlugin.list_plugins())
        plugins = handler.plugins_list()
        self.assertEqual(len(plugins['plugins-list']), plugins_count)
        self.assertIn('name', plugins['plugins-list'][0].keys())

        expected = {'pretty_name': 'Statuses',
                    'name': 'statuses', 'type': 'list'}
        self.assertEqual(plugins['plugins-list'][0]['statuses'], expected)

    def test_plugin_get(self):
        handler = hole.HoleHandler({}, 'plugin-list', MagicMock())
        plugin = handler.plugin_get(name='slack-notification')
        self.assertTrue(plugin)

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
        builder = await handler.builder_show(repo_name=self.repo.name,
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
        builder = await handler.builder_show(repo_name=self.repo.name,
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

    def test_get_action_methods(self):
        handler = hole.HoleHandler({}, 'action', MagicMock())
        expected = {'list_funcs': handler.list_funcs,
                    'repo_add': handler.repo_add,
                    'repo_get': handler.repo_get,
                    'repo_list': handler.repo_list,
                    'repo_remove': handler.repo_remove,
                    'repo_update': handler.repo_update,
                    'repo_add_slave': handler.repo_add_slave,
                    'repo_remove_slave': handler.repo_remove_slave,
                    'repo_add_branch': handler.repo_add_branch,
                    'repo_remove_branch': handler.repo_remove_branch,
                    'repo_enable_plugin': handler.repo_enable_plugin,
                    'repo_start_build': handler.repo_start_build,
                    'repo_disable_plugin': handler.repo_disable_plugin,
                    'repo_cancel_build': handler.repo_cancel_build,
                    'slave_add': handler.slave_add,
                    'slave_get': handler.slave_get,
                    'slave_list': handler.slave_list,
                    'slave_remove': handler.slave_remove,
                    'slave_update': handler.slave_update,
                    'buildset_list': handler.buildset_list,
                    'builder_list': handler.builder_list,
                    'plugins_list': handler.plugins_list,
                    'plugin_get': handler.plugin_get,
                    'builder_show': handler.builder_show,
                    'user_add': handler.user_add,
                    'user_remove': handler.user_remove,
                    'user_authenticate': handler.user_authenticate}

        action_methods = handler._get_action_methods()

        self.assertEqual(action_methods, expected)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_repo_dict(self):
        await self._create_test_data()
        self.repo.slaves = [self.slave]
        plugin = Mock()
        plugin.to_dict.return_value = {'name': 'myplugin'}
        self.repo.plugins = [plugin]

        handler = hole.HoleHandler({}, 'action', MagicMock())
        repo_dict = await handler._get_repo_dict(self.repo)

        self.assertIn('id', repo_dict)
        self.assertIn('slaves', repo_dict)
        self.assertTrue('status', repo_dict)
        self.assertTrue(repo_dict['slaves'][0]['name'])
        self.assertIn('parallel_builds', repo_dict.keys())

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_slave_dict(self):
        await self._create_test_data()

        handler = hole.HoleHandler({}, 'action', MagicMock())
        slave_dict = handler._get_slave_dict(self.slave)

        self.assertEqual(type(slave_dict['id']), str)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(repository.Repository, '_notify_repo_creation',
                  AsyncMagicMock())
    @patch.object(repository.utils, 'log', Mock())
    async def _create_test_data(self):
        self.slave = hole.Slave(name='name', host='127.0.0.1', port=7777,
                                token='123', owner=self.owner)
        await self.slave.save()
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
    def test_disconnectfromsignals(self):

        self.handler._disconnectfromsignals()
        self.assertTrue(all([hole.step_started.disconnect.called,
                             hole.step_finished.disconnect.called,
                             hole.build_started.disconnect.called,
                             hole.build_finished.disconnect.called,
                             hole.build_added.disconnect.called,
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
    @async_test
    async def test_connect2signals(self):

        repo = hole.Repository(url='https://bla.com/git', vcs_type='git',
                               owner=self.owner, name='my-repo')
        await repo.save()
        self.handler._handle_repo_status_changed = AsyncMagicMock()
        self.handler._handle_repo_added = AsyncMagicMock()
        self.handler._handle_ui_notifications = AsyncMagicMock(
            spec=self.handler._handle_ui_notifications)
        await self.handler._connect2signals()
        self.assertTrue(all([hole.step_started.connect.called,
                             hole.step_finished.connect.called,
                             hole.build_started.connect.called,
                             hole.build_finished.connect.called,
                             hole.build_added.connect.called,
                             hole.step_output_arrived.connect.called]))
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
        await self.handler.build_cancelled_fn(Mock())
        called = send_info.call_args[0][0]
        self.assertEqual(called, 'build_cancelled')

    @async_test
    async def test_handle(self):
        self.handler._connect2signals = AsyncMagicMock()
        send_response = MagicMock()
        self.handler.protocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))

        await self.handler.handle()

        self.assertTrue(self.handler._connect2signals.called)
        self.assertTrue(send_response.called)

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
        msg.body = dict(repository_id=testrepo.id,
                        old_status='running',
                        new_status='fail')
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
        f = self.handler.send_step_output_info(repo=testrepo,
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
