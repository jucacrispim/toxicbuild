# -*- coding: utf-8 -*-

# Copyright 2015-2019 Juca Crispim <juca@poraodojuca.net>

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
from collections import OrderedDict
from unittest import TestCase
from unittest.mock import MagicMock, patch
import tornado
from toxicbuild.ui import models, client
from tests import async_test, AsyncMagicMock


class BaseModelTest(TestCase):

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
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_change_password(self):
        requester = MagicMock()
        requester.email = 'a@a.com'
        ok = await models.User.change_password(requester, 'oldpwd', 'newpwd')
        self.assertTrue(ok)

    @patch.object(models.BaseModel, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_change_password_with_token(self):
        requester = MagicMock()
        requester.email = 'a@a.com'
        ok = await models.User.change_password_with_token('token', 'newpwd')
        self.assertTrue(ok)

    @patch.object(models.BaseModel, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_request_password_reset(self):
        requester = MagicMock()
        requester.email = 'a@a.com'
        ok = await models.User.request_password_reset(
            'a@a.com', 'https://bla.nada/reset?token={token}')
        self.assertTrue(ok)

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
        kw = OrderedDict(id='313lsjdf', vcs_type='git',
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

        kw = OrderedDict(name='localslave', host='localhost', port=7777,
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
                                            'localhost', 8888,
                                            '1233', owner, host='localslave')
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
                                       'builder': {'name': 'some'}}],
                           'repository': {'id': 'some-id'}},
                          {'id': 'paopofe', 'builds': [{}],
                           'repository': {'id': 'some-id'}}]))
    @async_test
    async def test_to_dict(self):
        requester = MagicMock()
        buildsets = await models.BuildSet.list(requester)
        buildset = buildsets[0]
        b_dict = buildset.to_dict('%s')
        self.assertTrue(b_dict['id'])
        self.assertTrue(b_dict['builds'][0]['steps'])
        self.assertTrue(b_dict['repository'])

    @patch.object(models.BuildSet, 'get_client', lambda requester:
                  get_client_mock(
                      requester,
                      {'id': 'sasdfasf',
                       'started': '3 9 25 08:53:38 2017 -0000',
                       'builds': [{'steps': [{'name': 'unit'}],
                                   'builder': {'name': 'some'}}]}))
    @async_test
    async def test_get(self):
        requester = MagicMock()
        buildset = await models.BuildSet.get(requester, 'some-id')
        self.assertTrue(buildset.id)


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


class BuildTest(TestCase):

    def test_to_dict(self):
        build = models.Build(MagicMock(),
                             ordered_kwargs={'builder': {'id': 'some-id'},
                                             'steps': [{'uuid': 'some'}]})
        d = build.to_dict()
        self.assertTrue(d['builder']['id'])
        self.assertTrue(d['steps'][0]['uuid'])

    @patch.object(models.Build, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  {'uuid': 'some-uuid', 'output': 'bla'}))
    @async_test
    def test_get(self):
        requester = MagicMock()
        build = yield from models.Build.get(requester, 'some-uuid')
        self.assertEqual(build.output, 'bla')
