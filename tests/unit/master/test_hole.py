# -*- coding: utf-8 -*-

# Copyright 2015,2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import MagicMock, Mock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.master import hole, build, repository, slave


class UIHoleTest(AsyncTestCase):

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @gen_test
    def test_client_connected_ok(self):
        uihole = hole.UIHole(Mock())
        uihole.data = {}
        uihole._stream_writer = Mock()
        # no exception means ok
        yield from uihole.client_connected()

    @patch.object(hole, 'UIStreamHandler', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @gen_test
    def test_client_connected_with_stream(self):
        uihole = hole.UIHole(Mock())
        uihole.data = {}
        uihole.action = 'stream'
        uihole._stream_writer = Mock()

        yield from uihole.client_connected()

        self.assertTrue(hole.UIStreamHandler.called)

    @patch.object(hole.HoleHandler, 'handle', MagicMock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', MagicMock())
    @gen_test
    def test_client_connected_error(self):

        @asyncio.coroutine
        def handle(*a, **kw):
            raise Exception('bla')

        hole.HoleHandler.handle = handle
        uihole = hole.UIHole(Mock())
        uihole.data = {}
        uihole._stream_writer = Mock()

        yield from uihole.client_connected()

        response = uihole.send_response.call_args[1]
        response_code = response['code']
        self.assertEqual(response_code, 1, response)


@patch.object(repository.utils, 'log', Mock())
class HoleHandlerTest(AsyncTestCase):

    @gen_test
    def tearDown(self):
        yield from asyncio.gather(*asyncio.Task.all_tasks())
        yield hole.Slave.drop_collection()
        yield hole.Repository.drop_collection()
        yield build.BuildSet.drop_collection()
        yield build.Builder.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_handle(self):
        protocol = MagicMock()
        handler = hole.HoleHandler({}, 'my-action', protocol)
        handler.my_action = lambda *a, **kw: None

        yield from handler.handle()
        code = protocol.send_response.call_args[1]['code']

        self.assertEqual(code, 0)

    @gen_test
    def test_handle_with_coro(self):
        protocol = MagicMock()
        handler = hole.HoleHandler({}, 'my-action', protocol)

        @asyncio.coroutine
        def my_action(*a, ** kw):
            return True

        handler.my_action = my_action

        yield from handler.handle()
        code = protocol.send_response.call_args[1]['code']

        self.assertEqual(code, 0)

    @gen_test
    def test_handle_with_not_known_action(self):
        handler = hole.HoleHandler({}, 'action', MagicMock())

        with self.assertRaises(hole.UIFunctionNotFound):
            yield from handler.handle()

    @gen_test
    def test_repo_add(self):
        yield from self._create_test_data()

        name = 'reponameoutro'
        url = 'git@somehere.com'
        vcs_type = 'git'
        update_seconds = 300
        slaves = ['name']
        action = 'repo-add'
        handler = hole.HoleHandler({}, action, MagicMock())

        repo = yield from handler.repo_add(name, url, update_seconds, vcs_type,
                                           slaves)

        self.assertTrue(repo['repo-add']['id'])

    @gen_test
    def test_repo_get_with_repo_name(self):
        yield from self._create_test_data()
        repo_name = 'reponame'
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())
        repo = (yield from handler.repo_get(repo_name=repo_name))['repo-get']

        self.assertEqual(repo['name'], repo_name)
        self.assertTrue(repo['id'])
        self.assertIn('status', repo.keys())

    @gen_test
    def test_repo_get_with_repo_url(self):
        yield from self._create_test_data()
        repo_url = 'git@somewhere.com'
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())
        repo = (yield from handler.repo_get(repo_url=repo_url))['repo-get']

        self.assertEqual(repo['url'], repo_url)

    @gen_test
    def test_repo_get_without_params(self):
        action = 'repo-get'
        handler = hole.HoleHandler({}, action, MagicMock())

        with self.assertRaises(TypeError):
            yield from handler.repo_get()

    @patch.object(repository, 'shutil', Mock())
    @gen_test
    def test_repo_remove(self):
        yield from self._create_test_data()
        action = 'repo-remove'
        handler = hole.HoleHandler({}, action, MagicMock())
        yield from handler.repo_remove(repo_name='reponame')

        self.assertEqual((yield hole.Repository.objects.count()), 1)

    @gen_test
    def test_repo_list(self):
        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'repo-list', MagicMock())
        repo_list = (yield from handler.repo_list())['repo-list']

        self.assertEqual(len(repo_list), 2)
        self.assertIn('status', repo_list[0].keys())

    @gen_test
    def test_repo_update(self):
        yield from self._create_test_data()

        data = {'url': 'git@somewhere.com',
                'update_seconds': 60}
        action = 'repo-update'
        handler = hole.HoleHandler(data, action, MagicMock())
        yield from handler.repo_update(repo_name=self.repo.name,
                                       update_seconds=60)
        repo = yield from hole.Repository.get(name=self.repo.name)

        self.assertEqual(repo.update_seconds, 60)

    @gen_test
    def test_repo_add_slave(self):
        yield from self._create_test_data()

        slave = yield from hole.Slave.create(name='name2',
                                             host='127.0.0.1', port=1234)

        repo_name = self.repo.name
        action = 'repo-add-slave'

        handler = hole.HoleHandler({}, action, MagicMock())

        yield from handler.repo_add_slave(repo_name=repo_name,
                                          slave_name='name2')

        repo = yield from hole.Repository.get(url=self.repo.url)

        self.assertEqual((yield repo.slaves)[0].id, slave.id)

    @gen_test
    def test_repo_remove_slave(self):
        yield from self._create_test_data()

        slave = yield from hole.Slave.create(name='name2', host='127.0.0.1',
                                             port=1234)
        yield from self.repo.add_slave(slave)

        handler = hole.HoleHandler({}, 'repo-remove-slave', MagicMock())

        yield from handler.repo_remove_slave(self.repo.name, slave.name)

        repo = yield from hole.Repository.get(url=self.repo.url)

        self.assertEqual(len((yield repo.slaves)), 0)

    @patch.object(repository, 'BuildManager', MagicMock(
        spec=repository.BuildManager))
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @gen_test
    def test_repo_start_build(self):
        yield from self._create_test_data()
        (yield self.revision.repository).build_manager\
            .get_builders = asyncio.coroutine(lambda s, r: [self.builders[0]])
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        yield self.repo.save()

        yield from handler.repo_start_build(self.repo.name, 'master')

        self.assertEqual(len(self.repo.add_builds_for_slave.call_args_list), 1)

    @patch.object(hole.HoleHandler, '_get_builders', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @gen_test
    def test_repo_start_build_with_builder_name(self):
        yield from self._create_test_data()
        hole.HoleHandler._get_builders = MagicMock(
            spec=hole.HoleHandler._get_builders)
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        yield self.repo.save()

        yield from handler.repo_start_build(self.repo.name, 'master',
                                            builder_name='b00')

        self.assertFalse(hole.HoleHandler._get_builders.called)
        self.assertEqual(len(self.repo.add_builds_for_slave.call_args_list), 1)

    @patch.object(repository, 'BuildManager', MagicMock())
    @patch.object(hole.RepositoryRevision, 'get', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @patch.object(hole.HoleHandler, '_get_builders', MagicMock())
    @gen_test
    def test_repo_start_build_with_named_tree(self):

        get_mock = MagicMock()

        @asyncio.coroutine
        def get(*a, **kw):
            get_mock()
            return self.revision

        hole.RepositoryRevision.get = get
        yield from self._create_test_data()

        hole.HoleHandler._get_builders = asyncio.coroutine(
            lambda s, r, builders=None: {self.slave: self.builders[0]})
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        yield self.repo.save()

        yield from handler.repo_start_build(self.repo.name, 'master',
                                            named_tree='123qewad')

        self.assertTrue(get_mock.called)

    @patch.object(repository, 'BuildManager', MagicMock())
    @patch.object(hole.Repository, 'add_builds_for_slave', MagicMock(
        spec=repository.Repository.add_builds_for_slave))
    @gen_test
    def test_repo_start_build_with_slave(self):
        yield from self._create_test_data()

        hole.HoleHandler._get_builders = asyncio.coroutine(
            lambda s, r, builders=None: {self.slave: self.builders[0]})
        handler = hole.HoleHandler({}, 'repo-start-build', MagicMock())
        self.repo.slaves = [self.slave]
        yield self.repo.save()

        yield from handler.repo_start_build(self.repo.name, 'master',
                                            slaves=['name'])

        self.assertEqual(len(self.repo.add_builds_for_slave.call_args_list), 1)

    @gen_test
    def test_slave_add(self):
        data = {'host': '127.0.0.1', 'port': 1234}
        handler = hole.HoleHandler(data, 'slave-add', MagicMock())
        slave = yield from handler.slave_add(slave_name='slave',
                                             slave_host='locahost',
                                             slave_port=1234)
        slave = slave['slave-add']

        self.assertTrue(slave['id'])

    @gen_test
    def test_slave_get(self):
        yield from self._create_test_data()
        slave_name = 'name'
        action = 'slave-get'
        handler = hole.HoleHandler({}, action, MagicMock())
        slave = (yield from handler.slave_get(
            slave_name=slave_name))['slave-get']

        self.assertEqual(slave['name'], slave_name)
        self.assertTrue(slave['id'])

    @gen_test
    def test_slave_remove(self):
        yield from self._create_test_data()
        data = {'host': '127.0.0.1', 'port': 7777}
        handler = hole.HoleHandler(data, 'slave-remove', MagicMock())
        yield from handler.slave_remove(slave_name='name')

        self.assertEqual((yield hole.Slave.objects.count()), 0)

    @gen_test
    def test_slave_list(self):
        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'slave-list', MagicMock())
        slaves = (yield from handler.slave_list())['slave-list']

        self.assertEqual(len(slaves), 1)

    @gen_test
    def test_buildset_list(self):
        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'buildset-list', MagicMock())
        buildsets = yield from handler.buildset_list(self.repo.name)
        buildsets = buildsets['buildset-list']

        self.assertEqual(len(buildsets), 3)
        self.assertEqual(len(buildsets[0]['builds']), 5)

    @gen_test
    def test_buildset_list_without_repo_name(self):

        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'buildset-list', MagicMock())

        builders = yield from handler.buildset_list()
        builders = builders['buildset-list']
        self.assertEqual(len(builders), 3)

    @gen_test
    def test_builder_list(self):
        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'builder-list', MagicMock())

        builders = (yield from handler.builder_list(
            id__in=[self.builders[0].id]))['builder-list']
        self.assertEqual(builders[0]['id'], str(self.builders[0].id))

    @gen_test
    def test_builder_show(self):
        yield from self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        handler = hole.HoleHandler(data, action, MagicMock())
        builder = yield from handler.builder_show(repo_name=self.repo.name,
                                                  builder_name='b01')
        builder = builder['builder-show']

        self.assertEqual(len(builder['buildsets']), 1)
        self.assertEqual(len(builder['buildsets'][0]['builds']), 3)

    @gen_test
    def test_builder_show_with_skip_and_offset(self):
        yield from self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        handler = hole.HoleHandler(data, action, MagicMock())
        builder = yield from handler.builder_show(repo_name=self.repo.name,
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
    @gen_test
    def test_get_builders(self):
        yield from self._create_test_data()
        (yield self.revision.repository).build_manager\
                                        .get_builders = asyncio.coroutine(
                                            lambda s, r: [self.builders[0]])
        slaves = [self.slave]
        expected = {self.slave: [self.builders[0]]}
        handler = hole.HoleHandler({}, 'action', self)

        builders = yield from handler._get_builders(slaves, self.revision)

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
                    'repo_start_build': handler.repo_start_build,
                    'slave_add': handler.slave_add,
                    'slave_get': handler.slave_get,
                    'slave_list': handler.slave_list,
                    'slave_remove': handler.slave_remove,
                    'buildset_list': handler.buildset_list,
                    'builder_list': handler.builder_list,
                    'builder_show': handler.builder_show}

        action_methods = handler._get_action_methods()

        self.assertEqual(action_methods, expected)

    @gen_test
    def test_get_repo_dict(self):
        yield from self._create_test_data()
        self.repo.slaves = [self.slave]

        handler = hole.HoleHandler({}, 'action', MagicMock())
        repo_dict = yield from handler._get_repo_dict(self.repo)

        self.assertIn('id', repo_dict)
        self.assertIn('slaves', repo_dict)
        self.assertTrue('status', repo_dict)
        self.assertTrue(repo_dict['slaves'][0]['name'])

    @gen_test
    def test_get_slave_dict(self):
        yield from self._create_test_data()

        handler = hole.HoleHandler({}, 'action', MagicMock())
        slave_dict = handler._get_slave_dict(self.slave)

        self.assertEqual(type(slave_dict['id']), str)

    @patch.object(repository.utils, 'log', Mock())
    @asyncio.coroutine
    def _create_test_data(self):

        self.slave = hole.Slave(name='name', host='127.0.0.1', port=7777)
        yield self.slave.save()
        self.repo = yield from hole.Repository.create(
            'reponame', 'git@somewhere.com', 300, 'git')
        self.other_repo = yield from hole.Repository.create(
            'other', 'git@bla.com', 300, 'git')

        self.builds = []
        now = datetime.now()
        for k in range(3):
            self.revision = repository.RepositoryRevision(
                repository=self.repo,
                commit='123qewad{}'.format(k),
                branch='master',
                commit_date=now, author='zé', title='boa!')
            yield self.revision.save()
            self.buildset = build.BuildSet(repository=self.repo,
                                           revision=self.revision,
                                           commit='asda',
                                           commit_date=now)
            yield self.buildset.save(revision=self.revision)
            builds = []
            self.builders = []
            for i in range(3):
                builder = build.Builder(name='b{}{}'.format(i, k),
                                        repository=self.repo)
                yield builder.save()
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
            yield self.buildset.save()


class UIStreamHandlerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        protocol = MagicMock()
        self.handler = hole.UIStreamHandler(protocol)

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def tearDown(self):
        yield build.BuildSet.drop_collection()
        yield build.Builder.drop_collection()
        yield slave.Slave.drop_collection()
        yield repository.Repository.drop_collection()

    @patch.object(hole, 'step_started', Mock())
    @patch.object(hole, 'step_finished', Mock())
    @patch.object(hole, 'build_started', Mock())
    @patch.object(hole, 'build_finished', Mock())
    def test_disconnectfromsignals(self):

        self.handler._disconnectfromsignals()
        self.assertTrue(all([hole.step_started.disconnect.called,
                             hole.step_finished.disconnect.called,
                             hole.build_started.disconnect.called,
                             hole.build_finished.disconnect.called]))

    @patch.object(hole, 'step_started', Mock())
    @patch.object(hole, 'step_finished', Mock())
    @patch.object(hole, 'build_started', Mock())
    @patch.object(hole, 'build_finished', Mock())
    def test_connect2signals(self):

        self.handler._connect2signals()
        self.assertTrue(all([hole.step_started.connect.called,
                             hole.step_finished.connect.called,
                             hole.build_started.connect.called,
                             hole.build_finished.connect.called]))

    def test_getattr(self):
        self.assertTrue(self.handler.step_started())

    def test_getattr_with_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.handler.i_dont_exist()

    @gen_test
    def test_handle(self):
        self.handler._connect2signals = Mock()
        self.handler.protocol.send_response = MagicMock()

        yield from self.handler.handle()

        self.assertTrue(self.handler._connect2signals.called)
        self.assertTrue(self.handler.protocol.send_response.called)

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', Mock())
    @gen_test
    def test_send_info_step(self):
        testrepo = yield from repository.Repository.create('name',
                                                           'git@git.nada',
                                                           300, 'git')
        testslave = yield from slave.Slave.create(name='name',
                                                  host='localhost',
                                                  port=1234)

        testbuilder = yield from build.Builder.create(name='b1',
                                                      repository=testrepo)
        testbuild = build.Build(repository=testrepo, slave=testslave,
                                branch='master', named_tree='master',
                                builder=testbuilder, status='running')

        teststep = build.BuildStep(name='s1', command='ls', status='running',
                                   output='')
        testbuild.steps.append(teststep)

        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.protocol.send_response = sr

        f = yield from self.handler.send_info('step-started',
                                              build=testbuild, step=teststep)
        yield from f

        self.assertEqual(self.CODE, 0)
        self.assertIn('build', self.BODY.keys())

    @patch.object(repository.Repository, 'schedule', Mock())
    @patch.object(hole.BaseToxicProtocol, 'send_response', Mock())
    @gen_test
    def test_send_info_build(self):
        testrepo = yield from repository.Repository.create('name',
                                                           'git@git.nada',
                                                           300, 'git')
        testslave = yield from slave.Slave.create(name='name',
                                                  host='localhost',
                                                  port=1234)
        testbuilder = yield from build.Builder.create(name='b1',
                                                      repository=testrepo)
        testbuild = build.Build(repository=testrepo, slave=testslave,
                                branch='master', named_tree='master',
                                builder=testbuilder, status='running')

        self.CODE = None
        self.BODY = None

        @asyncio.coroutine
        def sr(code, body):
            self.CODE = code
            self.BODY = body

        self.handler.protocol.send_response = sr

        f = yield from self.handler.send_info('step-started', build=testbuild)
        yield from f

        self.assertEqual(self.CODE, 0)
        self.assertIn('steps', self.BODY.keys())


class HoleServerTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.server = hole.HoleServer()

    def test_get_protocol_instance(self):
        prot = self.server.get_protocol_instance()

        self.assertEqual(hole.UIHole, type(prot))

    @patch.object(hole.asyncio, 'get_event_loop', Mock())
    @patch.object(hole.asyncio, 'async', Mock())
    def test_serve(self):
        self.server.serve()

        self.assertTrue(hole.asyncio.async.called)
