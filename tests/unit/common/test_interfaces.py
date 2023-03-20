# -*- coding: utf-8 -*-
# Copyright 2019-2020, 2023 Juca Crispim <juca@poraodojuca.net>

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


from collections import OrderedDict
import datetime
import json
from unittest import TestCase
from unittest.mock import MagicMock, patch, AsyncMock
from toxicbuild.common import interfaces, client
from tests import async_test


class BaseInterfaceTest(TestCase):

    def test_get_ref_cls(self):
        cls = 'toxicbuild.common.interfaces.BaseInterface'
        model = interfaces.BaseInterface(MagicMock(), ordered_kwargs={})
        new_cls = model._get_ref_cls(cls)
        self.assertIs(new_cls, interfaces.BaseInterface)

    def test_attributes_order(self):
        ordered = interfaces.OrderedDict()
        ordered['z'] = 1
        ordered['a'] = 2
        requester = MagicMock()
        model = interfaces.BaseInterface(requester, ordered)
        self.assertLess(model.__ordered__.index('z'),
                        model.__ordered__.index('a'))

    def test_datetime_attributes(self):
        requester = MagicMock()
        model = interfaces.BaseInterface(
            requester, {'somedt': '3 10 25 06:50:49 2017 +0000'})
        self.assertIsInstance(model.somedt, datetime.datetime)

    def test_to_dict(self):
        kw = interfaces.OrderedDict()
        kw['name'] = 'bla'
        kw['other'] = 'ble'
        kw['somedt'] = '3 10 25 06:50:49 2017 +0000'
        requester = MagicMock()
        instance = interfaces.BaseInterface(requester, kw)

        instance_dict = instance.to_dict('%d')

        expected = interfaces.OrderedDict()
        expected['name'] = 'bla'
        expected['other'] = 'ble'
        expected['somedt'] = interfaces.format_datetime(instance.somedt, '%d')
        self.assertEqual(expected, instance_dict)
        keys = list(instance_dict.keys())
        self.assertLess(keys.index('name'), keys.index('other'))

    def test_to_json(self):
        kw = interfaces.OrderedDict()
        kw['name'] = 'bla'
        kw['other'] = 'ble'
        requester = MagicMock()
        instance = interfaces.BaseInterface(requester, kw)

        instance_json = instance.to_json()

        expected = json.dumps(kw)
        self.assertEqual(expected, instance_json)

    def test_equal(self):
        class T(interfaces.BaseInterface):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = T(id='some-id')
        self.assertEqual(a, b)

    def test_unequal_id(self):
        class T(interfaces.BaseInterface):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = T(id='Other-id')
        self.assertNotEqual(a, b)

    def test_unequal_type(self):
        class T(interfaces.BaseInterface):

            def __init__(self, id=None):
                self.id = id

        class TT(interfaces.BaseInterface):

            def __init__(self, id=None):
                self.id = id

        a = T(id='some-id')
        b = TT(id='some-id')
        self.assertNotEqual(a, b)


class NotificationTest(TestCase):

    def setUp(self):
        self.notification = interfaces.NotificationInterface
        self.notification.settings = MagicMock()
        self.notification.settings.NOTIFICATIONS_API_TOKEN = 'asdf123'

    def test_get_headers(self):
        expected = {'Authorization': 'token: {}'.format(
            self.notification.settings.NOTIFICATIONS_API_TOKEN)}
        returned = self.notification._get_headers()
        self.assertEqual(expected, returned)

    @patch.object(interfaces.requests, 'get', AsyncMock(
        spec=interfaces.requests.get))
    @async_test
    async def test_list_no_repo(self):
        r = MagicMock()
        interfaces.requests.get.return_value = r
        r.json.return_value = {'notifications': [{'name': 'bla'}]}

        r = await self.notification.list()
        self.assertEqual(r[0].name, 'bla')

    @patch.object(interfaces.requests, 'get', AsyncMock(
        spec=interfaces.requests.get))
    @async_test
    async def test_list_for_repo(self):
        r = MagicMock()
        obj_id = 'fake-obj-id'
        interfaces.requests.get.return_value = r
        r.json.return_value = {'notifications': [{'name': 'bla'}]}

        r = await self.notification.list(obj_id)
        self.assertEqual(r[0].name, 'bla')

    @patch.object(interfaces.requests, 'post', AsyncMock(
        spec=interfaces.requests.post))
    @async_test
    async def test_enable(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'
        config = {'webhook_url': 'https://somewebhook.url'}
        expected_config = {'webhook_url': 'https://somewebhook.url',
                           'repository_id': obj_id}
        expected_url = '{}/{}'.format(self.notification.api_url(),
                                      notif_name)
        await self.notification.enable(obj_id, notif_name, **config)
        called_url = interfaces.requests.post.call_args[0][0]
        called_config = json.loads(
            interfaces.requests.post.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)

    @patch.object(interfaces.requests, 'delete', AsyncMock(
        spec=interfaces.requests.delete))
    @async_test
    async def test_disable(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'
        expected_config = {'repository_id': obj_id}
        expected_url = '{}/{}'.format(self.notification.api_url(),
                                      notif_name)
        await self.notification.disable(obj_id, notif_name)
        called_url = interfaces.requests.delete.call_args[0][0]
        called_config = json.loads(
            interfaces.requests.delete.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)

    @patch.object(interfaces.requests, 'put', AsyncMock(
        spec=interfaces.requests.put))
    @async_test
    async def test_update(self):
        obj_id = 'fake-obj-id'
        notif_name = 'slack-notification'

        expected_url = '{}/{}'.format(self.notification.api_url(),
                                      notif_name)
        config = {'webhook_url': 'https://somewebhook.url'}
        expected_config = {'webhook_url': 'https://somewebhook.url',
                           'repository_id': obj_id}

        await self.notification.update(obj_id, notif_name, **config)
        called_url = interfaces.requests.put.call_args[0][0]
        called_config = json.loads(
            interfaces.requests.put.call_args[1]['data'])

        self.assertEqual(expected_url, called_url)
        self.assertEqual(expected_config, called_config)


class BaseHoleInterfaceTest(TestCase):

    @patch.object(interfaces, 'get_hole_client', AsyncMock(
        spec=interfaces.get_hole_client))
    @patch.object(interfaces.BaseHoleInterface, 'settings', MagicMock())
    @async_test
    async def test_get_client(self):
        requester = MagicMock()
        await interfaces.BaseHoleInterface.get_client(requester)
        self.assertTrue(interfaces.get_hole_client.called)

    @patch.object(interfaces, 'get_hole_client', MagicMock(
        spec=interfaces.get_hole_client))
    @async_test
    async def test_get_client_client_exists(self):
        try:
            requester = MagicMock()
            client = MagicMock()
            client.connect = AsyncMock()
            interfaces.BaseHoleInterface._client = client
            client = await interfaces.BaseHoleInterface.get_client(requester)
            self.assertEqual(client, interfaces.BaseHoleInterface._client)
            self.assertFalse(client.connect.called)
        finally:
            interfaces.BaseHoleInterface._client = None

    @patch.object(interfaces, 'get_hole_client', MagicMock(
        spec=interfaces.get_hole_client))
    @async_test
    async def test_get_client_client_exists_disconnected(self):
        try:
            requester = MagicMock()
            client = MagicMock()
            client.connect = AsyncMock()
            interfaces.BaseHoleInterface._client = client
            interfaces.BaseHoleInterface._client._connected = False
            client = await interfaces.BaseHoleInterface.get_client(requester)
            self.assertEqual(client, interfaces.BaseHoleInterface._client)
            self.assertTrue(client.connect.called)
        finally:
            interfaces.BaseHoleInterface._client = None


async def get_client_mock(requester, r2s_return_value=None):
    requester = MagicMock()
    cl = client.HoleClient(requester, 'localhost', 6666, hole_token='asdf')

    async def r2s(action, body):
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


@patch.object(interfaces.BaseHoleInterface, 'settings', MagicMock())
class UserInterfaceTest(TestCase):

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, {'id': 'some-id',
                                         'email': 'some-email@bla.com'}))
    @async_test
    async def test_authenticate(self):
        user = await interfaces.UserInterface.authenticate(
            'some-email@bla.com', 'asdf')
        self.assertEqual(user.id, 'some-id')

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_change_password(self):
        requester = MagicMock()
        requester.email = 'a@a.com'
        ok = await interfaces.UserInterface.change_password(
            requester, 'oldpwd', 'newpwd')
        self.assertTrue(ok)

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_change_password_with_token(self):
        requester = MagicMock()
        requester.email = 'a@a.com'
        ok = await interfaces.UserInterface.change_password_with_token(
            'token', 'newpwd')
        self.assertTrue(ok)

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_request_password_reset(self):
        requester = MagicMock()
        requester.email = 'a@a.com'
        ok = await interfaces.UserInterface.request_password_reset(
            'a@a.com', 'https://bla.nada/reset?token={token}')
        self.assertTrue(ok)

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, {'id': 'some-id',
                                         'email': 'some-email@bla.com'}))
    @async_test
    async def test_add(self):
        user = await interfaces.UserInterface.add('some-email@bla.com',
                                                  'some-guy', 'asdf',
                                                  ['add_repo'])

        self.assertEqual(user.id, 'some-id')

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, 'ok'))
    @async_test
    async def test_delete(self):
        requester = MagicMock()
        requester.id = 'asdf'
        user = interfaces.UserInterface(requester, {'id': 'some-id'})
        r = await user.delete()
        self.assertEqual(r, 'ok')

    @patch.object(interfaces.BaseHoleInterface, 'get_client', lambda requester:
                  get_client_mock(None, False))
    @async_test
    async def test_exists(self):
        exists = await interfaces.UserInterface.exists(username='some-guy')
        self.assertFalse(exists)

    @patch.object(interfaces.UserInterface, 'get_client', get_client_mock)
    @async_test
    async def test_get(self):
        user = await interfaces.UserInterface.get(username='the-user')
        self.assertTrue(user.id)


class RepositoryTest(TestCase):

    def setUp(self):
        super().setUp()
        kw = OrderedDict(id='313lsjdf', vcs_type='git',
                         update_seconds=300, slaves=[],
                         name='my-repo')

        self.requester = MagicMock()
        self.repository = interfaces.RepositoryInterface(self.requester, kw)

        self.repository.get_client = get_client_mock

    @patch.object(interfaces.RepositoryInterface, 'get_client',
                  get_client_mock)
    @async_test
    async def test_add(self):
        owner = MagicMock()
        owner.id = 'some-id'
        repo = await interfaces.RepositoryInterface.add(
            self.requester, 'some-repo', 'git@somewhere.com', owner, 'git')
        self.assertTrue(repo.id)

    @patch.object(interfaces.RepositoryInterface, 'get_client',
                  get_client_mock)
    @async_test
    async def test_get(self):
        requester = MagicMock()
        repo = await interfaces.RepositoryInterface.get(
            requester, name='some-repo')
        self.assertTrue(repo.id)

    @patch.object(interfaces.RepositoryInterface, 'get_client',
                  get_client_mock)
    @async_test
    async def test_repo_slaves(self):
        requester = MagicMock()
        repo = await interfaces.RepositoryInterface.get(
            requester, name='some-repo')
        self.assertEqual(type(repo.slaves[0]), interfaces.SlaveInterface)

    @patch.object(interfaces.RepositoryInterface, 'get_client',
                  lambda requester:
                  get_client_mock(requester,
                                  [{'name': 'repo0'}, {'name': 'repo1'}]))
    @async_test
    async def test_list(self):
        requester = MagicMock()
        repos = await interfaces.RepositoryInterface.list(requester)
        self.assertEqual(len(repos), 2)

    @async_test
    async def test_delete(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'ok')

        resp = await self.repository.delete()
        self.assertEqual(resp, 'ok')

    @async_test
    async def test_add_slave(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'add slave ok')

        kw = OrderedDict(name='localslave', host='localhost', port=7777,
                         token='123', id='some-id')
        requester = MagicMock()
        slave = interfaces.SlaveInterface(requester, kw)
        resp = await self.repository.add_slave(slave)

        self.assertEqual(resp, 'add slave ok')

    @async_test
    async def test_remove_slave(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'remove slave ok')
        kw = dict(name='localslave', host='localhost', port=7777,
                  id='some-id')
        requester = MagicMock()
        slave = interfaces.SlaveInterface(requester, kw)
        resp = await self.repository.remove_slave(slave)

        self.assertEqual(resp, 'remove slave ok')

    @async_test
    async def test_add_branch(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'add branch ok')

        resp = await self.repository.add_branch('master', False)

        self.assertEqual(resp, 'add branch ok')

    @async_test
    async def test_remove_branch(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'remove branch ok')

        resp = await self.repository.remove_branch('master')

        self.assertEqual(resp, 'remove branch ok')

    @async_test
    async def test_start_build(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'start build ok')

        resp = await self.repository.start_build('master',
                                                 builder_name_or_id='b0',
                                                 named_tree='v0.1')

        self.assertEqual(resp, 'start build ok')

    def test_to_dict(self):
        requester = MagicMock()
        kw = dict(name='bla')
        self.repository.slaves = [interfaces.SlaveInterface(requester, kw)]
        repo_dict = self.repository.to_dict()
        self.assertTrue(isinstance(repo_dict['slaves'][0], dict))

    def test_to_dict_lastbuildset(self):
        requester = MagicMock()
        kw = dict(name='bla')
        buildset = interfaces.BuildSetInterface(
            requester, ordered_kwargs={'bla': 'ble'})
        self.repository.last_buildset = buildset
        self.repository.slaves = [interfaces.SlaveInterface(requester, kw)]
        repo_dict = self.repository.to_dict()
        self.assertTrue(isinstance(repo_dict['slaves'][0], dict))

    @async_test
    async def test_update(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'ok')
        resp = await self.repository.update(update_seconds=1000)
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

    @async_test
    async def test_request_code_update(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-request-code-update')

        resp = await self.repository.request_code_update()
        self.assertEqual(resp, 'repo-request-code-update')

    @async_test
    async def test_add_envvars(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-add-envvars')

        resp = await self.repository.add_envvars()
        self.assertEqual(resp, 'repo-add-envvars')

    @async_test
    async def test_rm_envvars(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-rm-envvars')

        resp = await self.repository.rm_envvars()
        self.assertEqual(resp, 'repo-rm-envvars')

    @async_test
    async def test_replace_envvars(self):
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-replace-envvars')

        resp = await self.repository.replace_envvars(**{})
        self.assertEqual(resp, 'repo-replace-envvars')

    @async_test
    async def test_list_branches_id(self):
        self.repository.id = 'a-id'
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-list-branches-response')

        resp = await self.repository.list_branches()
        self.assertEqual(resp, 'repo-list-branches-response')

    @async_test
    async def test_list_branches_full_name(self):
        self.repository.id = ''
        self.repository.full_name = 'user/repo'
        self.repository.get_client = lambda requester: get_client_mock(
            requester, 'repo-list-branches-response')

        resp = await self.repository.list_branches()
        self.assertEqual(resp, 'repo-list-branches-response')


class SlaveTest(TestCase):

    @patch.object(interfaces.SlaveInterface, 'get_client', lambda requester:
                  get_client_mock(
                      requester, {'host': 'localhost'}))
    @async_test
    async def test_add(self):
        requester = MagicMock()
        owner = MagicMock()
        owner.id = 'some-id'
        slave = await interfaces.SlaveInterface.add(requester,
                                                    'localhost', 8888,
                                                    '1233', owner,
                                                    host='localslave')
        self.assertEqual(slave.host, 'localhost')

    @patch.object(interfaces.SlaveInterface, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  {'host': 'localhost', 'name': 'slave'}))
    @async_test
    async def test_get(self):
        requester = MagicMock()
        slave = await interfaces.SlaveInterface.get(requester, name='slave')
        self.assertEqual(slave.name, 'slave')

    @patch.object(interfaces.SlaveInterface, 'get_client', lambda requester:
                  get_client_mock(
                      requester, [{'name': 'slave0'}, {'name': 'slave1'}]))
    @async_test
    async def test_list(self):
        requester = MagicMock()
        slaves = await interfaces.SlaveInterface.list(requester)
        self.assertEqual(len(slaves), 2)

    @async_test
    async def test_delete(self):
        requester = MagicMock()
        kw = dict(name='slave', host='localhost', port=1234,
                  id='some=id')
        slave = interfaces.SlaveInterface(requester, kw)
        slave.get_client = lambda requester: get_client_mock(
            requester, 'ok')

        resp = await slave.delete()
        self.assertEqual(resp, 'ok')

    @async_test
    async def test_update(self):
        requester = MagicMock()
        kw = dict(name='slave', host='localhost', port=1234,
                  id='some=id')
        slave = interfaces.SlaveInterface(requester, kw)
        slave.get_client = lambda requester: get_client_mock(
            requester, 'ok')

        resp = await slave.update(port=4321)
        self.assertEqual(resp, 'ok')


class BuildSetTest(TestCase):

    @patch.object(interfaces.BuildSetInterface, 'get_client', AsyncMock(
        spec=interfaces.BuildSetInterface.get_client))
    @async_test
    async def test_list(self):
        requester = MagicMock()
        client = MagicMock()
        client.__enter__.return_value = client
        client.buildset_list = AsyncMock()
        client.buildset_list.return_value = [
            {'id': 'sasdfasf',
             'started': '3 9 25 08:53:38 2017 -0000',
             'builds': [{'steps': [{'name': 'unit'}],
                         'builder': {'name': 'some'}}]},
            {'id': 'paopofe', 'builds': [{}]}]
        interfaces.BuildSetInterface.get_client.return_value = client
        buildsets = await interfaces.BuildSetInterface.list(requester)
        r = await client.buildset_list()
        self.assertEqual(len(buildsets), 2, r)
        self.assertTrue(len(buildsets[0].builds[0].steps), 1)

    @patch.object(interfaces.BuildSetInterface, 'get_client', lambda requester:
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
        buildsets = await interfaces.BuildSetInterface.list(requester)
        buildset = buildsets[0]
        b_dict = buildset.to_dict('%s')
        self.assertTrue(b_dict['id'])
        self.assertTrue(b_dict['builds'][0]['steps'])
        self.assertTrue(b_dict['repository'])

    @patch.object(interfaces.BuildSetInterface, 'get_client', lambda requester:
                  get_client_mock(
                      requester,
                      {'id': 'sasdfasf',
                       'started': '3 9 25 08:53:38 2017 -0000',
                       'builds': [{'steps': [{'name': 'unit'}],
                                   'builder': {'name': 'some'}}]}))
    @async_test
    async def test_get(self):
        requester = MagicMock()
        buildset = await interfaces.BuildSetInterface.get(requester, 'some-id')
        self.assertTrue(buildset.id)


class BuilderTest(TestCase):

    @patch.object(interfaces.BuilderInterface, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  [{'id': 'sasdfasf', 'name': 'b0',
                                    'status': 'running'},
                                   {'id': 'paopofe', 'name': 'b1',
                                    'status': 'success'}]))
    @async_test
    async def test_list(self):
        requester = MagicMock()
        builders = await interfaces.BuilderInterface.list(requester,
                                                          id__in=['sasdfasf',
                                                                  'paopofe'])

        self.assertEqual(len(builders), 2)
        self.assertEqual(builders[0].name, 'b0')


class BuildTest(TestCase):

    def test_to_dict(self):
        build = interfaces.BuildInterface(
            MagicMock(),
            ordered_kwargs={'builder': {'id': 'some-id'},
                            'steps': [{'uuid': 'some'}]})
        d = build.to_dict()
        self.assertTrue(d['builder']['id'])
        self.assertTrue(d['steps'][0]['uuid'])

    @patch.object(interfaces.BuildInterface, 'get_client', lambda requester:
                  get_client_mock(requester,
                                  {'uuid': 'some-uuid', 'output': 'bla'}))
    @async_test
    async def test_get(self):
        requester = MagicMock()
        build = await interfaces.BuildInterface.get(requester, 'some-uuid')
        self.assertEqual(build.output, 'bla')


class StepInterfaceTest(TestCase):

    @patch.object(interfaces.StepInterface, 'get_client',
                  AsyncMock(return_value=MagicMock()))
    @async_test
    async def test_get(self):
        client = interfaces.StepInterface.get_client.return_value.\
            __enter__.return_value
        client.buildstep_get = AsyncMock(return_value={})
        requester = MagicMock()
        step = await interfaces.StepInterface.get(requester, 'a-uuid')
        self.assertTrue(client.buildstep_get.called)
        self.assertTrue(step)


class WaterfallInterfaceTest(TestCase):

    @patch.object(
        interfaces.WaterfallInterface, 'get_client', lambda requester:
        get_client_mock(
            requester,
            {'buildsets': [
                {'id': 'sasdfasf',
                 'started': '3 9 25 08:53:38 2017 -0000',
                 'builds': [{'steps': [{'name': 'unit'}],
                             'builder': {'name': 'some'}}]},
                {'id': 'paopofe', 'builds': [{}]}],
             'branches': ['master', 'dev'],
             'builders': [{'id': 'sasdfasf', 'name': 'b0',
                           'status': 'running'}]}))
    @async_test
    async def test_get(self):
        requester = MagicMock()
        waterfall = await interfaces.WaterfallInterface.get(
            requester, 'some-repo-id')
        self.assertTrue(waterfall.buildsets)

    @patch.object(
        interfaces.WaterfallInterface, 'get_client', lambda requester:
        get_client_mock(
            requester,
            {'buildsets': [
                {'id': 'sasdfasf',
                 'started': '3 9 25 08:53:38 2017 -0000',
                 'builds': [{'steps': [{'name': 'unit'}],
                             'builder': {'name': 'some'}}]},
                {'id': 'paopofe', 'builds': []}],
             'branches': ['master', 'dev'],
             'builders': [{'id': 'sasdfasf', 'name': 'b0',
                           'status': 'running'}]}))
    @async_test
    async def test_to_dict(self):
        requester = MagicMock()
        waterfall = await interfaces.WaterfallInterface.get(
            requester, 'some-repo-id')
        d = waterfall.to_dict('%s')
        self.assertTrue(d['builders'])
        self.assertTrue(d['buildsets'])
