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
from toxicbuild.master import hole, build, repository, slave, plugins
from tests import async_test


class UIHoleTest(TestCase):

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
        uihole.data = {}
        uihole._stream_writer = Mock()
        # no exception means ok
        status = await uihole.client_connected()
        self.assertEqual(status, 0)

    @patch.object(hole, 'UIStreamHandler', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @async_test
    async def test_client_connected_with_stream(self):
        send_response = MagicMock()
        hole.BaseToxicProtocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))
        uihole = hole.UIHole(Mock())
        uihole.data = {}
        uihole.action = 'stream'
        uihole._stream_writer = Mock()

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

        hole.HoleHandler.handle = handle
        uihole = hole.UIHole(Mock())
        uihole.data = {}
        uihole._stream_writer = Mock()

        await uihole.client_connected()

        response = send_response.call_args[1]
        response_code = response['code']
        self.assertEqual(response_code, 1, response)


@patch.object(repository.utils, 'log', Mock())
class HoleHandlerTest(TestCase):

    @async_test
    async def tearDown(self):
        await hole.Slave.drop_collection()
        await hole.Repository.drop_collection()
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()

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

    @async_test
    async def test_repo_add(self):
        await self._create_test_data()

        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        action = 'repo-add'
        handler = hole.HoleHandler({}, action, MagicMock())

        repo = await handler.repo_add(name, url, update_seconds, vcs_type,
                                      slaves)

        self.assertTrue(repo['repo-add']['id'])

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

        repo = await handler.repo_add(name, url, update_seconds, vcs_type,
                                      slaves, parallel_builds=1)

        self.assertEqual(repo['repo-add']['parallel_builds'], 1)

    @async_test
    async def test_repo_get_with_repo_name(self):
        await self._create_test_data()
        repo_name = 'reponame'
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())
        repo = (await handler.repo_get(repo_name=repo_name))['repo-get']

        self.assertEqual(repo['name'], repo_name)
        self.assertTrue(repo['id'])
        self.assertIn('status', repo.keys())

    @async_test
    async def test_repo_get_with_repo_url(self):
        await self._create_test_data()
        repo_url = 'git@somewhere.com'
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())
        repo = (await handler.repo_get(repo_url=repo_url))['repo-get']

        self.assertEqual(repo['url'], repo_url)

    @async_test
    async def test_repo_get_without_params(self):
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())

        with self.assertRaises(TypeError):
            await handler.repo_get()

    @patch.object(repository, 'shutil', Mock())
    @async_test
    async def test_repo_remove(self):
        await self._create_test_data()
        action = 'repo-remove'
        handler = hole.HoleHandler({}, action, MagicMock())
        await handler.repo_remove(repo_name='reponame')
        allrepos = [r.name for r in (
            await hole.Repository.objects.to_list())]
        self.assertEqual((await hole.Repository.objects.count()),
                         1, allrepos)

    @async_test
    async def test_repo_enable_plugin(self):

        class TestPlugin(plugins.MasterPlugin):
            name = 'test-hole-plugin'
            type = 'test'

            @asyncio.coroutine
            def run(self):
                pass

        await self._create_test_data()
        action = 'repo-enable-plugin'
        handler = hole.HoleHandler({}, action, MagicMock())
        await handler.repo_enable_plugin(self.repo.name,
                                         'test-hole-plugin')
        repo = await hole.Repository.get(id=self.repo.id)
        self.assertEqual(len(repo.plugins), 1)

    @async_test
    async def test_repo_disable_plugin(self):

        class TestPlugin(plugins.MasterPlugin):
            name = 'test-hole-plugin'
            type = 'test'

            @asyncio.coroutine
            def run(self):
                pass

        await self._create_test_data()
        action = 'repo-enable-plugin'
        handler = hole.HoleHandler({}, action, MagicMock())
        await handler.repo_enable_plugin(self.repo.name,
                                         'test-hole-plugin')
        kw = {'name': 'test-hole-plugin'}
        await handler.repo_disable_plugin(self.repo.name, **kw)
        repo = await hole.Repository.get(id=self.repo.id)
        self.assertEqual(len(repo.plugins), 0)

    @async_test
    async def test_repo_list(self):
        await self._create_test_data()
        handler = hole.HoleHandler({}, 'repo-list', MagicMock())
        repo_list = (await handler.repo_list())['repo-list']

        self.assertEqual(len(repo_list), 2)
        self.assertIn('status', repo_list[0].keys())

    @async_test
    async def test_repo_update(self):
        await self._create_test_data()

        data = {'url': 'git@somewhere.com',
                'update_seconds': 60}
        action = 'repo-update'
        handler = hole.HoleHandler(data, action, MagicMock())
        await handler.repo_update(repo_name=self.repo.name,
                                  update_seconds=60)
        repo = await hole.Repository.get(name=self.repo.name)

        self.assertEqual(repo.update_seconds, 60)

    @async_test
    async def test_repo_update_with_slaves(self):
        await self._create_test_data()

        data = {'url': 'git@somewhere.com',
                'update_seconds': 60}
        action = 'repo-update'
        handler = hole.HoleHandler(data, action, MagicMock())
        slaves = ['name']
        await handler.repo_update(repo_name=self.repo.name,
                                  update_seconds=60, slaves=slaves)
        repo = await hole.Repository.get(name=self.repo.name)

        self.assertEqual(repo.update_seconds, 60)

    @async_test
    async def test_repo_add_slave(self):
        await self._create_test_data()

        slave = await hole.Slave.create(name='name2',
                                             host='127.0.0.1', port=1234,
                                             token='asdf')

        repo_name = self.repo.name
        action = 'repo-add-slave'

        handler = hole.HoleHandler({}, action, MagicMock())

        await handler.repo_add_slave(repo_name=repo_name,
                                     slave_name='name2')

        repo = await hole.Repository.get(url=self.repo.url)

        self.assertEqual((await repo.slaves)[0].id, slave.id)

    @async_test
    async def test_repo_remove_slave(self):
        await self._create_test_data()

        slave = await hole.Slave.create(name='name2', host='127.0.0.1',
                                             port=1234, token='123')
        await self.repo.add_slave(slave)

        handler = hole.HoleHandler({}, 'repo-remove-slave', MagicMock())

        await handler.repo_remove_slave(self.repo.name, slave.name)

        repo = await hole.Repository.get(url=self.repo.url)

        self.assertEqual(len((await repo.slaves)), 0)

    @async_test
    async def test_repo_add_branch(self):
        await self._create_test_data()
        action = 'repo-add-branch'

        handler = hole.HoleHandler({}, action, MagicMock())

        await handler.repo_add_branch(repo_name=self.repo.name,
                                      branch_name='release',
                                      notify_only_latest=True)

        repo = await hole.Repository.get(url=self.repo.url)

        self.assertEqual(len(repo.branches), 1)

    @async_test
    async def test_repo_remove_branch(self):
        await self._create_test_data()
        action = 'repo-add-branch'

        handler = hole.HoleHandler({}, action, MagicMock())

        await handler.repo_add_branch(repo_name=self.repo.name,
                                      branch_name='release',
                                      notify_only_latest=True)
        repo = await hole.Repository.get(url=self.repo.url)
        branch_count = len(repo.branches)
        await handler.repo_remove_branch(repo_name=self.repo.name,
                                         branch_name='release')

        repo = await hole.Repository.get(url=self.repo.url)

        self.assertEqual(len(repo.branches), branch_count - 1)

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
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        await self.repo.save()

        await handler.repo_start_build(self.repo.name, 'master')

        self.assertEqual(len(add_builds_for_slave.call_args_list), 1)

    @patch.object(hole.HoleHandler, '_get_builders', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @async_test
    async def test_repo_start_build_with_builder_name(self):
        add_builds_for_slave = MagicMock()
        hole.Repository.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))
        await self._create_test_data()
        hole.HoleHandler._get_builders = MagicMock(
            spec=hole.HoleHandler._get_builders)
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        await self.repo.save()

        await handler.repo_start_build(self.repo.name, 'master',
                                       builder_name='b00')

        self.assertFalse(hole.HoleHandler._get_builders.called)
        self.assertEqual(len(add_builds_for_slave.call_args_list), 1)

    @patch.object(repository, 'BuildManager', MagicMock())
    @patch.object(hole.RepositoryRevision, 'get', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @patch.object(hole.HoleHandler, '_get_builders', MagicMock())
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

        hole.RepositoryRevision.get = get
        await self._create_test_data()

        hole.HoleHandler._get_builders = asyncio.coroutine(
            lambda s, r, builders=None: {self.slave: self.builders[0]})
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        await self.repo.save()

        await handler.repo_start_build(self.repo.name, 'master',
                                       named_tree='123qewad')

        self.assertTrue(get_mock.called)

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
            lambda s, r, builders=None: {self.slave: self.builders[0]})
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        await self.repo.save()

        await handler.repo_start_build(self.repo.name, 'master',
                                       slaves=['name'])

        self.assertEqual(len(add_builds_for_slave.call_args_list), 1)

    @async_test
    async def test_slave_add(self):
        data = {'host': '127.0.0.1', 'port': 1234}
        handler = hole.HoleHandler(data, 'slave-add', MagicMock())
        slave = await handler.slave_add(slave_name='slave',
                                        slave_host='locahost',
                                        slave_port=1234,
                                        slave_token='1234')
        slave = slave['slave-add']

        self.assertTrue(slave['id'])

    @async_test
    async def test_slave_get(self):
        await self._create_test_data()
        slave_name = 'name'
        action = 'slave-get'
        handler = hole.HoleHandler({}, action, MagicMock())
        slave = (await handler.slave_get(
            slave_name=slave_name))['slave-get']

        self.assertEqual(slave['name'], slave_name)
        self.assertTrue(slave['id'])

    @async_test
    async def test_slave_remove(self):
        await self._create_test_data()
        data = {'host': '127.0.0.1', 'port': 7777}
        handler = hole.HoleHandler(data, 'slave-remove', MagicMock())
        await handler.slave_remove(slave_name='name')
        await asyncio.sleep(0.1)
        self.assertEqual((await hole.Slave.objects.count()), 0)

    @async_test
    async def test_slave_list(self):
        await self._create_test_data()
        handler = hole.HoleHandler({}, 'slave-list', MagicMock())
        slaves = (await handler.slave_list())['slave-list']

        self.assertEqual(len(slaves), 1)

    @async_test
    async def test_slave_update(self):
        await self._create_test_data()

        data = {'host': '10.0.0.1', 'slave_name': self.slave.name}
        action = 'slave-update'
        handler = hole.HoleHandler(data, action, MagicMock())
        await handler.slave_update(slave_name=self.slave.name,
                                   host='10.0.0.1')
        slave = await hole.Slave.get(name=self.slave.name)
        self.assertEqual(slave.host, '10.0.0.1')

    @async_test
    async def test_buildset_list(self):
        await self._create_test_data()
        handler = hole.HoleHandler({}, 'buildset-list', MagicMock())
        buildsets = await handler.buildset_list(self.repo.name)
        buildsets = buildsets['buildset-list']

        self.assertEqual(len(buildsets), 3)
        self.assertEqual(len(buildsets[0]['builds']), 5)

    @async_test
    async def test_buildset_list_without_repo_name(self):

        await self._create_test_data()
        handler = hole.HoleHandler({}, 'buildset-list', MagicMock())

        builders = await handler.buildset_list()
        builders = builders['buildset-list']
        self.assertEqual(len(builders), 3)

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

    @async_test
    async def test_builder_show(self):
        await self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        handler = hole.HoleHandler(data, action, MagicMock())
        builder = await handler.builder_show(repo_name=self.repo.name,
                                             builder_name='b01')
        builder = builder['builder-show']

        self.assertEqual(len(builder['buildsets']), 1)
        self.assertEqual(len(builder['buildsets'][0]['builds']), 3)

    @async_test
    async def test_builder_show_with_skip_and_offset(self):
        await self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        handler = hole.HoleHandler(data, action, MagicMock())
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

    @patch.object(repository, 'BuildManager', MagicMock())
    @async_test
    async def test_get_builders(self):
        await self._create_test_data()
        (await self.revision.repository).build_manager\
            .get_builders = asyncio.coroutine(
            lambda s, r: [self.builders[0]])
        slaves = [self.slave]
        expected = {self.slave: [self.builders[0]]}
        handler = hole.HoleHandler({}, 'action', self)

        builders = await handler._get_builders(slaves, self.revision)

        self.assertEqual(builders, expected)

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
                    'slave_add': handler.slave_add,
                    'slave_get': handler.slave_get,
                    'slave_list': handler.slave_list,
                    'slave_remove': handler.slave_remove,
                    'slave_update': handler.slave_update,
                    'buildset_list': handler.buildset_list,
                    'builder_list': handler.builder_list,
                    'plugins_list': handler.plugins_list,
                    'plugin_get': handler.plugin_get,
                    'builder_show': handler.builder_show}

        action_methods = handler._get_action_methods()

        self.assertEqual(action_methods, expected)

    @async_test
    async def test_get_repo_dict(self):
        await self._create_test_data()
        self.repo.slaves = [self.slave]
        self.repo.plugins = [{'_name': 'myplugin'}]

        handler = hole.HoleHandler({}, 'action', MagicMock())
        repo_dict = await handler._get_repo_dict(self.repo)

        self.assertIn('id', repo_dict)
        self.assertIn('slaves', repo_dict)
        self.assertTrue('status', repo_dict)
        self.assertTrue(repo_dict['slaves'][0]['name'])
        self.assertIn('parallel_builds', repo_dict.keys())

    @async_test
    async def test_get_slave_dict(self):
        await self._create_test_data()

        handler = hole.HoleHandler({}, 'action', MagicMock())
        slave_dict = handler._get_slave_dict(self.slave)

        self.assertEqual(type(slave_dict['id']), str)

    @patch.object(repository.utils, 'log', Mock())
    async def _create_test_data(self):
        self.slave = hole.Slave(name='name', host='127.0.0.1', port=7777,
                                token='123')
        await self.slave.save()
        self.repo = await hole.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git')
        self.other_repo = await hole.Repository.create(
            'other', 'git@bla.com', 300, 'git')

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


@patch.object(hole.UIStreamHandler, 'log', Mock())
class UIStreamHandlerTest(TestCase):

    def setUp(self):
        super().setUp()
        protocol = MagicMock()
        self.handler = hole.UIStreamHandler(protocol)

    @async_test
    async def tearDown(self):
        await build.BuildSet.drop_collection()
        await build.Builder.drop_collection()
        await slave.Slave.drop_collection()
        await repository.Repository.drop_collection()

    @patch.object(hole, 'step_started', Mock())
    @patch.object(hole, 'step_finished', Mock())
    @patch.object(hole, 'build_started', Mock())
    @patch.object(hole, 'build_finished', Mock())
    @patch.object(hole, 'repo_status_changed', Mock())
    @patch.object(hole, 'build_added', Mock())
    @patch.object(hole, 'step_output_arrived', Mock())
    def test_disconnectfromsignals(self):

        self.handler._disconnectfromsignals()
        self.assertTrue(all([hole.step_started.disconnect.called,
                             hole.step_finished.disconnect.called,
                             hole.build_started.disconnect.called,
                             hole.build_finished.disconnect.called,
                             hole.repo_status_changed.disconnect.called,
                             hole.build_added.disconnect.called,
                             hole.step_output_arrived.disconnect.called]))

    @patch.object(hole, 'step_started', Mock())
    @patch.object(hole, 'step_finished', Mock())
    @patch.object(hole, 'build_started', Mock())
    @patch.object(hole, 'build_finished', Mock())
    @patch.object(hole, 'repo_status_changed', Mock())
    @patch.object(hole, 'build_added', Mock())
    @patch.object(hole, 'step_output_arrived', Mock())
    def test_connect2signals(self):

        self.handler._connect2signals()
        self.assertTrue(all([hole.step_started.connect.called,
                             hole.step_finished.connect.called,
                             hole.build_started.connect.called,
                             hole.build_finished.connect.called,
                             hole.repo_status_changed.connect.called,
                             hole.build_added.connect.called,
                             hole.step_output_arrived.connect.called]))

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
    async def test_handle(self):
        self.handler._connect2signals = Mock()
        send_response = MagicMock()
        self.handler.protocol.send_response = asyncio.coroutine(
            lambda *a, **kw: send_response(*a, **kw))

        await self.handler.handle()

        self.assertTrue(self.handler._connect2signals.called)
        self.assertTrue(send_response.called)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', Mock())
    @async_test
    async def test_send_info_step(self):
        testrepo = await repository.Repository.create('name',
                                                      'git@git.nada',
                                                      300, 'git')
        testslave = await slave.Slave.create(name='name',
                                                  host='localhost',
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
                                     build=testbuild, step=teststep)

        await asyncio.sleep(0)
        self.assertEqual(self.CODE, 0)
        self.assertIn('build', self.BODY.keys())

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', Mock())
    @async_test
    async def test_send_info_build(self):
        testrepo = await repository.Repository.create('name',
                                                      'git@git.nada',
                                                      300, 'git')
        testslave = await slave.Slave.create(name='name',
                                                  host='localhost',
                                                  port=1234,
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
        await self.handler.send_info('step-started', build=testbuild)
        await asyncio.sleep(0)
        self.assertEqual(self.CODE, 0)
        self.assertIn('steps', self.BODY.keys())
        self.assertIn('buildset', self.BODY.keys())

        self.assertIsInstance(self.BODY['slave']['id'], str)
        self.assertIsInstance(self.BODY['repository']['id'], str)

    @async_test
    async def test_send_repo_status_info(self):
        testslave = await slave.Slave.create(name='name',
                                                  host='localhost',
                                                  port=1234,
                                                  token='123')

        testrepo = await repository.Repository.create('name',
                                                      'git@git.nada',
                                                      300, 'git',
                                                      slaves=[testslave])
        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.send_response = sr
        await self.handler.send_repo_status_info(repo=testrepo,
                                                 old_status='running',
                                                 new_status='fail')

        await asyncio.sleep(0)
        self.assertEqual(self.BODY['status'], 'fail')
        self.assertIsInstance(self.BODY['id'], str)

    @async_test
    async def test_send_step_output_info(self):
        testslave = await slave.Slave.create(name='name',
                                                  host='localhost',
                                                  port=1234,
                                                  token='123')

        testrepo = await repository.Repository.create('name',
                                                      'git@git.nada',
                                                      300, 'git',
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
