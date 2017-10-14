# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch
import tornado
from toxicbuild.ui import models, client
from tests import async_test


class BaseModelTest(TestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models, 'get_hole_client', MagicMock(
        spec=models.get_hole_client))
    @async_test
    def test_get_client(self):
        yield from models.BaseModel.get_client()
        self.assertTrue(models.get_hole_client.called)

    def test_to_dict(self):
        instance = models.BaseModel(name='bla', other='ble')

        instance_dict = instance.to_dict()

        expected = {'name': 'bla', 'other': 'ble'}
        self.assertEqual(expected, instance_dict)

    def test_to_json(self):
        instance = models.BaseModel(name='bla', other='ble')

        instance_json = instance.to_json()

        expected = json.dumps({'name': 'bla', 'other': 'ble'})
        self.assertEqual(expected, instance_json)

    def test_equal(self):
        class T(models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = T(id='some-id')
        self.assertEqual(a, b)

    def test_unequal_id(self):
        class T(models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = T(id='Other-id')
        self.assertNotEqual(a, b)

    def test_unequal_type(self):
        class T(models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        class TT(models.BaseModel):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = TT(id='some-id')
        self.assertNotEqual(a, b)


@asyncio.coroutine
def get_client_mock(r2s_return_value=None):
    cl = client.UIHoleClient('localhost', 6666)

    @asyncio.coroutine
    def r2s(action, body):
        if r2s_return_value is None:
            return {'id': '23sfs34', 'vcs_type': 'git', 'name': 'my-repo',
                    'update_seconds': 300, 'slaves':
                    [{'name': 'bla', 'id': '123sd', 'host': 'localhost',
                      'port': 1234}]}
        else:
            return r2s_return_value

    cl.request2server = r2s
    cl._connected = True
    cl.writer = MagicMock()
    return cl


class PluginTest(TestCase):

    @patch.object(models.Plugin, 'get_client', lambda:
                  get_client_mock([{'name': 'some-plugin', 'type': 'test',
                                    'somefield': 'list',
                                    'otherfield': 'string'}]))
    @async_test
    def test_list(self):
        plugins = yield from models.Plugin.list()
        self.assertEqual(plugins[0].name, 'some-plugin')

    @patch.object(models.Plugin, 'get_client', lambda:
                  get_client_mock({'name': 'some-plugin', 'type': 'test',
                                   'somefield': 'list',
                                   'otherfield': 'string'}))
    @async_test
    def test_get(self):
        plugin = yield from models.Plugin.get('some-plugin')
        self.assertEqual(plugin.name, 'some-plugin')


class RepositoryTest(TestCase):

    def setUp(self):
        super().setUp()
        self.repository = models.Repository(id='313lsjdf', vcs_type='git',
                                            update_seconds=300, slaves=[],
                                            name='my-repo')

        self.repository.get_client = get_client_mock

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @async_test
    def test_add(self):
        repo = yield from models.Repository.add('some-repo',
                                                'git@somewhere.com', 'git')
        self.assertTrue(repo.id)

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @async_test
    def test_get(self):

        repo = yield from models.Repository.get(name='some-repo')
        self.assertTrue(repo.id)

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @async_test
    def test_repo_slaves(self):
        repo = yield from models.Repository.get(name='some-repo')
        self.assertEqual(type(repo.slaves[0]), models.Slave)

    @patch.object(models.Repository, 'get_client', lambda:
                  get_client_mock([{'name': 'repo0'}, {'name': 'repo1'}]))
    @async_test
    def test_list(self):

        repos = yield from models.Repository.list()
        self.assertEqual(len(repos), 2)

    @async_test
    def test_delete(self):
        self.repository.get_client = lambda: get_client_mock('ok')

        resp = yield from self.repository.delete()
        self.assertEqual(resp, 'ok')

    @async_test
    def test_add_slave(self):
        self.repository.get_client = lambda: get_client_mock('add slave ok')

        slave = models.Slave(name='localslave', host='localhost', port=7777,
                             token='123')
        resp = yield from self.repository.add_slave(slave)

        self.assertEqual(resp, 'add slave ok')

    @async_test
    def test_remove_slave(self):
        self.repository.get_client = lambda: get_client_mock('remove slave ok')

        slave = models.Slave(name='localslave', host='localhost', port=7777)
        resp = yield from self.repository.remove_slave(slave)

        self.assertEqual(resp, 'remove slave ok')

    @async_test
    def test_add_branch(self):
        self.repository.get_client = lambda: get_client_mock('add branch ok')

        resp = yield from self.repository.add_branch('master', False)

        self.assertEqual(resp, 'add branch ok')

    @async_test
    def test_remove_branch(self):
        self.repository.get_client = lambda: get_client_mock(
            'remove branch ok')

        resp = yield from self.repository.remove_branch('master')

        self.assertEqual(resp, 'remove branch ok')

    @async_test
    def test_start_build(self):
        self.repository.get_client = lambda: get_client_mock('start build ok')

        resp = yield from self.repository.start_build('master',
                                                      builder_name='b0',
                                                      named_tree='v0.1')

        self.assertEqual(resp, 'start build ok')

    def test_to_dict(self):
        self.repository.slaves = [models.Slave(name='bla')]
        repo_dict = self.repository.to_dict()
        self.assertTrue(isinstance(repo_dict['slaves'][0], dict))

    @async_test
    def test_update(self):
        self.repository.get_client = lambda: get_client_mock('ok')
        resp = yield from self.repository.update(update_seconds=1000)
        self.assertEqual(resp, 'ok')

    @async_test
    def test_enable_plugin(self):
        self.repository.get_client = lambda: get_client_mock('ok')

        resp = yield from self.repository.enable_plugin('some-plugin',
                                                        bla='bla',
                                                        ble=0)

        self.assertEqual(resp, 'ok')

    @async_test
    def test_disable_plugin(self):
        self.repository.get_client = lambda: get_client_mock('ok')

        resp = yield from self.repository.disable_plugin(name='some-plugin')

        self.assertEqual(resp, 'ok')


class SlaveTest(TestCase):

    @patch.object(models.Slave, 'get_client', lambda: get_client_mock(
        {'host': 'localhost'}))
    @async_test
    def test_add(self):

        slave = yield from models.Slave.add('localslave', 'localhost', 8888,
                                            '1233')
        self.assertEqual(slave.host, 'localhost')

    @patch.object(models.Slave, 'get_client', lambda: get_client_mock(
        {'host': 'localhost', 'name': 'slave'}))
    @async_test
    def test_get(self):

        slave = yield from models.Slave.get(name='slave')
        self.assertEqual(slave.name, 'slave')

    @patch.object(models.Slave, 'get_client', lambda: get_client_mock(
        [{'name': 'slave0'}, {'name': 'slave1'}]))
    @async_test
    def test_list(self):

        slaves = yield from models.Slave.list()
        self.assertEqual(len(slaves), 2)

    @async_test
    def test_delete(self):
        slave = models.Slave(name='slave', host='localhost', port=1234)
        slave.get_client = lambda: get_client_mock('ok')

        resp = yield from slave.delete()
        self.assertEqual(resp, 'ok')

    @async_test
    def test_update(self):
        slave = models.Slave(name='slave', host='localhost', port=1234)
        slave.get_client = lambda: get_client_mock('ok')

        resp = yield from slave.update(port=4321)
        self.assertEqual(resp, 'ok')


class BuildSetTest(TestCase):

    @patch.object(models.BuildSet, 'get_client', lambda: get_client_mock(
        [{'id': 'sasdfasf', 'builds': [{'steps': [{'name': 'unit'}]}]},
         {'id': 'paopofe', 'builds': [{}]}]))
    @async_test
    def test_list(self):

        builders = yield from models.BuildSet.list()
        self.assertEqual(len(builders), 2)
        self.assertTrue(len(builders[0].builds[0].steps), 1)


class BuilderTest(TestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models.Builder, 'get_client', lambda: get_client_mock(
        [{'id': 'sasdfasf', 'name': 'b0', 'status': 'running'},
         {'id': 'paopofe', 'name': 'b1', 'status': 'success'}]))
    @async_test
    def test_list(self):
        builders = yield from models.Builder.list(id__in=['sasdfasf',
                                                          'paopofe'])

        self.assertEqual(len(builders), 2)
        self.assertEqual(builders[0].name, 'b0')
