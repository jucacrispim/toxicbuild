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
import datetime
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch
import tornado
from toxicbuild.ui import models, client, settings
from tests import async_test, AsyncMagicMock


class BaseModelTest(TestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models, 'get_hole_client', MagicMock(
        spec=models.get_hole_client))
    @async_test
    def test_get_client(self):
        requester = MagicMock()
        yield from models.BaseModel.get_client(requester)
        self.assertTrue(models.get_hole_client.called)

    @patch.object(models, 'get_hole_client', MagicMock(
        spec=models.get_hole_client))
    @async_test
    def test_get_client_client_exists(self):
        try:
            requester = MagicMock()
            models.BaseModel._client = MagicMock()
            client = yield from models.BaseModel.get_client(requester)
            self.assertEqual(client, models.BaseModel._client)
            self.assertFalse(client.connect.called)
        finally:
            models.BaseModel._client = None

    @patch.object(models, 'get_hole_client', MagicMock(
        spec=models.get_hole_client))
    @async_test
    def test_get_client_client_exists_disconnected(self):
        try:
            requester = MagicMock()
            models.BaseModel._client = MagicMock()
            models.BaseModel._client._connected = False
            client = yield from models.BaseModel.get_client(requester)
            self.assertEqual(client, models.BaseModel._client)
            self.assertTrue(client.connect.called)
        finally:
            models.BaseModel._client = None

    def test_attributes_order(self):
        ordered = models.OrderedDict()
        ordered['z'] = 1
        ordered['a'] = 2
        requester = MagicMock()
        model = models.BaseModel(requester, ordered)
        self.assertLess(model.__ordered__.index('z'),
                        model.__ordered__.index('a'))

    def test_datetime_attributes(self):
        requester = MagicMock()
        model = models.BaseModel(requester,
                                 {'somedt': '3 10 25 06:50:49 2017 +0000'})
        self.assertIsInstance(model.somedt, datetime.datetime)

    def test_to_dict(self):
        kw = models.OrderedDict()
        kw['name'] = 'bla'
        kw['other'] = 'ble'
        kw['somedt'] = '3 10 25 06:50:49 2017 +0000'
        requester = MagicMock()
        instance = models.BaseModel(requester, kw)

        instance_dict = instance.to_dict()

        expected = models.OrderedDict()
        expected['name'] = 'bla'
        expected['other'] = 'ble'
        expected['somedt'] = models.format_datetime(instance.somedt)
        self.assertEqual(expected, instance_dict)
        keys = list(instance_dict.keys())
        self.assertLess(keys.index('name'), keys.index('other'))

    def test_to_json(self):
        kw = models.OrderedDict()
        kw['name'] = 'bla'
        kw['other'] = 'ble'
        requester = MagicMock()
        instance = models.BaseModel(requester, kw)

        instance_json = instance.to_json()

        expected = json.dumps(kw)
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
def get_client_mock(requester, r2s_return_value=None):
    requester = MagicMock()
    cl = client.UIHoleClient(requester, 'localhost', 6666)

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


class UserTest(TestCase):

    @patch.object(models.BaseModel, 'get_client', lambda requester:
                  get_client_mock(None, {'id': 'some-id',
                                         'email': 'some-email@bla.com'}))
    @async_test
    async def test_authenticate(self):
        user = await models.User.authenticate('some-email@bla.com', 'asdf')
        self.assertEqual(user.id, 'some-id')

    @patch.object(models.BaseModel, 'get_client', lambda requester:
                  get_client_mock(None, {'id': 'some-id',
                                         'email': 'some-email@bla.com'}))
    @async_test
    async def test_add(self):
        user = await models.User.add('some-email@bla.com',
                                     'some-guy', 'asdf',
                                     ['add_repo'])
        self.assertEqual(user.id, 'some-id')

    @patch.object(models.BaseModel, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_delete(self):
        requester = MagicMock()
        requester.id = 'asdf'
        user = models.User(requester, {'id': 'some-id'})
        r = await user.delete()
        self.assertEqual(r, 'ok')

    @patch.object(models.BaseModel, 'get_client', lambda requester:
                  get_client_mock(None, False))
    @async_test
    async def test_exists(self):
        exists = await models.User.exists(username='some-guy')
        self.assertFalse(exists)


class RepositoryTest(TestCase):

    def setUp(self):
        super().setUp()
        kw = models.OrderedDict(id='313lsjdf', vcs_type='git',
                                update_seconds=300, slaves=[],
                                name='my-repo')

        self.requester = MagicMock()
        self.repository = models.Repository(self.requester, kw)

        self.repository.get_client = get_client_mock

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @async_test
    def test_add(self):
        owner = MagicMock()
        owner.id = 'some-id'
        repo = yield from models.Repository.add(self.requester, 'some-repo',
                                                'git@somewhere.com', owner,
                                                'git')
        self.assertTrue(repo.id)

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @async_test
    def test_get(self):
        requester = MagicMock()
        repo = yield from models.Repository.get(requester, name='some-repo')
        self.assertTrue(repo.id)

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @async_test
    def test_repo_slaves(self):
        requester = MagicMock()
        repo = yield from models.Repository.get(requester, name='some-repo')
        self.assertEqual(type(repo.slaves[0]), models.Slave)

    @patch.object(models.Repository, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  [{'name': 'repo0'}, {'name': 'repo1'}]))
    @async_test
    def test_list(self):
        requester = MagicMock()
        repos = yield from models.Repository.list(requester)
        self.assertEqual(len(repos), 2)

    @async_test
    def test_delete(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'ok')

        resp = yield from self.repository.delete()
        self.assertEqual(resp, 'ok')

    @async_test
    def test_add_slave(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'add slave ok')

        kw = models.OrderedDict(name='localslave', host='localhost', port=7777,
                                token='123', id='some-id')
        requester = MagicMock()
        slave = models.Slave(requester, kw)
        resp = yield from self.repository.add_slave(slave)

        self.assertEqual(resp, 'add slave ok')

    @async_test
    def test_remove_slave(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'remove slave ok')
        kw = dict(name='localslave', host='localhost', port=7777,
                  id='some-id')
        requester = MagicMock()
        slave = models.Slave(requester, kw)
        resp = yield from self.repository.remove_slave(slave)

        self.assertEqual(resp, 'remove slave ok')

    @async_test
    def test_add_branch(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'add branch ok')

        resp = yield from self.repository.add_branch('master', False)

        self.assertEqual(resp, 'add branch ok')

    @async_test
    def test_remove_branch(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'remove branch ok')

        resp = yield from self.repository.remove_branch('master')

        self.assertEqual(resp, 'remove branch ok')

    @async_test
    def test_start_build(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'start build ok')

        resp = yield from self.repository.start_build('master',
                                                      builder_name='b0',
                                                      named_tree='v0.1')

        self.assertEqual(resp, 'start build ok')

    def test_to_dict(self):
        requester = MagicMock()
        kw = dict(name='bla')
        self.repository.slaves = [models.Slave(requester, kw)]
        repo_dict = self.repository.to_dict()
        self.assertTrue(isinstance(repo_dict['slaves'][0], dict))

    def test_to_dict_lastbuildset(self):
        requester = MagicMock()
        kw = dict(name='bla')
        buildset = models.BuildSet(requester, ordered_kwargs={'bla': 'ble'})
        self.repository.last_buildset = buildset
        self.repository.slaves = [models.Slave(requester, kw)]
        repo_dict = self.repository.to_dict()
        self.assertTrue(isinstance(repo_dict['slaves'][0], dict))

    @async_test
    def test_update(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'ok')
        resp = yield from self.repository.update(update_seconds=1000)
        self.assertEqual(resp, 'ok')

    @async_test
    async def test_cancel_build(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'build-cancelled')

        resp = await self.repository.cancel_build('some-build-uuid')
        self.assertEqual(resp, 'build-cancelled')

    @async_test
    async def test_enable(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-enable')

        resp = await self.repository.enable()
        self.assertEqual(resp, 'repo-enable')

    @async_test
    async def test_disable(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-disable')

        resp = await self.repository.disable()
        self.assertEqual(resp, 'repo-disable')


class SlaveTest(TestCase):

    @patch.object(models.Slave, 'get_client', lambda requester:
                  get_client_mock(
                      requester, {'host': 'localhost'}))
    @async_test
    def test_add(self):
        requester = MagicMock()
        owner = MagicMock()
        owner.id = 'some-id'
        slave = yield from models.Slave.add(requester,
                                            'localslave', 'localhost', 8888,
                                            '1233', owner)
        self.assertEqual(slave.host, 'localhost')

    @patch.object(models.Slave, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  {'host': 'localhost', 'name': 'slave'}))
    @async_test
    def test_get(self):
        requester = MagicMock()
        slave = yield from models.Slave.get(requester, name='slave')
        self.assertEqual(slave.name, 'slave')

    @patch.object(models.Slave, 'get_client', lambda requester:
                  get_client_mock(
                      requester, [{'name': 'slave0'}, {'name': 'slave1'}]))
    @async_test
    def test_list(self):
        requester = MagicMock()
        slaves = yield from models.Slave.list(requester)
        self.assertEqual(len(slaves), 2)

    @async_test
    def test_delete(self):
        requester = MagicMock()
        kw = dict(name='slave', host='localhost', port=1234,
                  id='some=id')
        slave = models.Slave(requester, kw)
        slave.get_client = lambda requester: get_client_mock(
            requester, 'ok')

        resp = yield from slave.delete()
        self.assertEqual(resp, 'ok')

    @async_test
    def test_update(self):
        requester = MagicMock()
        kw = dict(name='slave', host='localhost', port=1234,
                  id='some=id')
        slave = models.Slave(requester, kw)
        slave.get_client = lambda requester: get_client_mock(
            requester, 'ok')

        resp = yield from slave.update(port=4321)
        self.assertEqual(resp, 'ok')


class BuildSetTest(TestCase):

    @patch.object(models.BuildSet, 'get_client', AsyncMagicMock(
        spec=models.BuildSet.get_client))
    @async_test
    async def test_list(self):
        requester = MagicMock()
        client = MagicMock()
        client.__enter__.return_value = client
        client.buildset_list = AsyncMagicMock()
        client.buildset_list.return_value = [
            {'id': 'sasdfasf',
             'started': '3 9 25 08:53:38 2017 -0000',
             'builds': [{'steps': [{'name': 'unit'}],
                         'builder': {'name': 'some'}}]},
            {'id': 'paopofe', 'builds': [{}]}]
        models.BuildSet.get_client.return_value = client
        buildsets = await models.BuildSet.list(requester)
        r = await client.buildset_list()
        self.assertEqual(len(buildsets), 2, r)
        self.assertTrue(len(buildsets[0].builds[0].steps), 1)

    @patch.object(models.BuildSet, 'get_client', lambda requester:
                  get_client_mock(
                      requester, [
                          {'id': 'sasdfasf',
                           'started': '3 9 25 08:53:38 2017 -0000',
                           'builds': [{'steps': [{'name': 'unit'}],
                                       'builder': {'name': 'some'}}]},
                          {'id': 'paopofe', 'builds': [{}]}]))
    @async_test
    async def test_to_dict(self):
        requester = MagicMock()
        buildsets = await models.BuildSet.list(requester)
        buildset = buildsets[0]
        b_dict = buildset.to_dict()
        self.assertTrue(b_dict['id'])
        self.assertTrue(b_dict['builds'][0]['steps'])


class BuilderTest(TestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models.Builder, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  [{'id': 'sasdfasf', 'name': 'b0',
                                    'status': 'running'},
                                   {'id': 'paopofe', 'name': 'b1',
                                    'status': 'success'}]))
    @async_test
    def test_list(self):
        requester = MagicMock()
        builders = yield from models.Builder.list(requester,
                                                  id__in=['sasdfasf',
                                                          'paopofe'])

        self.assertEqual(len(builders), 2)
        self.assertEqual(builders[0].name, 'b0')


class NotificationTest(TestCase):

    def setUp(self):
        self.notification = models.Notification

    def test_get_headers(self):
        expected = {'Authorization': 'token {}'.format(
            settings.NOTIFICATIONS_API_TOKEN)}
        returned = self.notification._get_headers()
        self.assertEqual(expected, returned)

    @patch.object(models.requests, 'get', AsyncMagicMock(
        spec=models.requests.get))
    @async_test
    async def test_list_no_repo(self):
        r = MagicMock()
        models.requests.get.return_value = r
        r.json.return_value = {'notifications': [{'name': 'bla'}]}

        r = await self.notification.list()
        self.assertEqual(r[0].name, 'bla')

    @patch.object(models.requests, 'get', AsyncMagicMock(
        spec=models.requests.get))
    @async_test
    async def test_list_for_repo(self):
        r = MagicMock()
        obj_id = 'fake-obj-id'
        models.requests.get.return_value = r
        r.json.return_value = {'notifications': [{'name': 'bla'}]}

        r = await self.notification.list(obj_id)
        self.assertEqual(r[0].name, 'bla')

    @patch.object(models.requests, 'post', AsyncMagicMock(
        spec=models.requests.post))
    @async_test
    async def test_enable(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'
        config = {'webhook_url': 'https://somewebhook.url'}
        expected_config = {'webhook_url': 'https://somewebhook.url',
                           'repository_id': obj_id}
        expected_url = '{}/{}'.format(self.notification.api_url,
                                      notif_name)
        await self.notification.enable(obj_id, notif_name, **config)
        called_url = models.requests.post.call_args[0][0]
        called_config = json.loads(models.requests.post.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)

    @patch.object(models.requests, 'delete', AsyncMagicMock(
        spec=models.requests.delete))
    @async_test
    async def test_disable(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'
        expected_config = {'repository_id': obj_id}
        expected_url = '{}/{}'.format(self.notification.api_url,
                                      notif_name)
        await self.notification.disable(obj_id, notif_name)
        called_url = models.requests.delete.call_args[0][0]
        called_config = json.loads(models.requests.delete.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)

    @patch.object(models.requests, 'put', AsyncMagicMock(
        spec=models.requests.put))
    @async_test
    async def test_update(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'

        expected_url = '{}/{}'.format(self.notification.api_url,
                                      notif_name)
        config = {'webhook_url': 'https://somewebhook.url'}
        expected_config = {'webhook_url': 'https://somewebhook.url',
                           'repository_id': obj_id}

        await self.notification.update(obj_id, notif_name, **config)
        called_url = models.requests.put.call_args[0][0]
        called_config = json.loads(models.requests.put.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)


class BuildTest(TestCase):

    def test_to_dict(self):
        build = models.Build(MagicMock(),
                             ordered_kwargs={'builder': {'id': 'some-id'},
                                             'steps': [{'uuid': 'some'}]})
        d = build.to_dict()
        self.assertTrue(d['builder']['id'])
        self.assertTrue(d['steps'][0]['uuid'])
