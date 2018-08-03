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
from unittest.mock import patch, Mock
from toxicbuild.core import BaseToxicClient
from toxicbuild.master import settings
from toxicbuild.master.repository import Repository
from toxicbuild.master.users import User
from toxicbuild.master.exchanges import scheduler_action
from tests import async_test
from tests.functional import BaseFunctionalTest, REPO_DIR


class DummyUIClient(BaseToxicClient):

    def __init__(self, user, *args, **kwargs):
        kwargs['use_ssl'] = True
        kwargs['validate_cert'] = False
        super().__init__(*args, **kwargs)
        self.user = user

    @asyncio.coroutine
    def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'user_id': str(self.user.id),
                'token': '123'}
        yield from self.write(data)
        response = yield from self.get_response()
        return response['body'][action]

    @asyncio.coroutine
    def create_slave(self):
        action = 'slave-add'
        body = {'slave_name': 'test-slave',
                'slave_host': 'localhost',
                'slave_port': settings.SLAVE_PORT,
                'slave_token': '123',
                'owner_id': str(self.user.id),
                'use_ssl': True,
                'validate_cert': False}

        resp = yield from self.request2server(action, body)
        return resp

    @asyncio.coroutine
    def create_repo(self):
        action = 'repo-add'
        body = {'repo_name': 'test-repo', 'repo_url': REPO_DIR,
                'vcs_type': 'git', 'update_seconds': 1,
                'slaves': ['test-slave'],
                'owner_id': str(self.user.id)}

        resp = yield from self.request2server(action, body)

        return resp

    async def create_user(self):
        action = 'user-add'
        body = {'username': 'ze', 'email': 'ze@ze.com', 'password': 'asdf',
                'allowed_actions': ['add_user', 'add_repo']}
        resp = await self.request2server(action, body)
        return resp

    async def user_authenticate(self):
        action = 'user-authenticate'
        body = {'username_or_email': 'ze@ze.com', 'password': 'asdf'}
        resp = await self.request2server(action, body)
        return resp

    async def remove_user(self):
        action = 'user-remove'
        body = {'email': 'ze@ze.com'}
        resp = await self.request2server(action, body)
        return resp

    @asyncio.coroutine
    def start_build(self, builder='builder-1'):

        action = 'repo-start-build'
        body = {'repo_name_or_id': 'toxic/test-repo',
                'branch': 'master'}
        if builder:
            body['builder_name'] = builder
        resp = yield from self.request2server(action, body)

        return resp

    @asyncio.coroutine
    def get_stream(self):

        action = 'stream'
        self.write({'action': action, 'body': {}})

        resp = yield from self.get_response()
        while resp:
            yield resp
            resp = yield from self.get_response()

    @asyncio.coroutine
    def wait_clone(self):
        yield from self.write({'action': 'stream', 'token': '123',
                               'body': {},
                               'user_id': str(self.user.id)})
        while True:
            r = yield from self.get_response()
            body = r['body'] if r else {}
            try:
                event = body['event_type']
                if event == 'repo_status_changed':
                    break
            except KeyError:
                pass

    @asyncio.coroutine
    def enable_plugin(self):
        action = 'repo-enable-plugin'
        body = {'repo_name_or_id': 'toxic/test-repo',
                'plugin_name': 'custom-webhook',
                'webhook_url': 'http://localhost:{}/webhookmessage/'.format(
                    settings.WEBHOOK_PORT),
                'branches': ['master'],
                'statuses': ['running', 'fail', 'success']}

        resp = yield from self.request2server(action, body)
        return resp

    @asyncio.coroutine
    def disable_plugin(self):
        action = 'repo-disable-plugin'
        body = {'repo_name_or_id': 'toxic/test-repo',
                'plugin_name': 'slack-notification'}

        resp = yield from self.request2server(action, body)
        return resp


@asyncio.coroutine
def get_dummy_client(user):
    dc = DummyUIClient(user, settings.HOLE_ADDR, settings.HOLE_PORT)
    yield from dc.connect()
    return dc


class ToxicMasterTest(BaseFunctionalTest):

    @classmethod
    @async_test
    async def setUpClass(cls):
        super().setUpClass()

        user = User(email='toxic@test.com', is_superuser=True)
        user.set_password('1234')
        await user.save()
        cls.user = user

    @classmethod
    @patch('aioamqp.protocol.logger', Mock())
    @async_test
    async def tearDownClass(cls):
        try:
            await cls._delete_test_data()
        except OSError:
            pass

        await User.drop_collection()
        await Repository.drop_collection()
        await scheduler_action.declare()
        await scheduler_action.queue_delete()
        await scheduler_action.connection.disconnect()
        super().tearDownClass()

    @async_test
    async def tearDown(self):
        await Repository.objects(name__not__exists=1).delete()
        await Repository.objects(name=None).delete()
        await Repository.objects(url=None).delete()

    @async_test
    def test_01_create_slave(self):
        with (yield from get_dummy_client(self.user)) as client:
            response = yield from client.create_slave()
        self.assertTrue(response)

    @async_test
    def test_02_list_slaves(self):
        with (yield from get_dummy_client(self.user)) as client:
            slaves = yield from client.request2server('slave-list', {})

        self.assertEqual(len(slaves), 1)

    @async_test
    def test_03_create_repo(self):
        with (yield from get_dummy_client(self.user)) as client:
            response = yield from client.create_repo()

        with (yield from get_dummy_client(self.user)) as client:
            yield from client.wait_clone()

        self.assertTrue(response)

    @async_test
    def test_04_list_repos(self):
        with (yield from get_dummy_client(self.user)) as client:
            repos = yield from client.request2server('repo-list', {})

        self.assertEqual(len(repos), 1)
        self.assertEqual(len(repos[0]['slaves']), 1)

    @async_test
    def test_05_repo_add_slave(self):
        with (yield from get_dummy_client(self.user)) as client:
            yield from client.request2server('slave-add',
                                             {'slave_name': 'test-slave2',
                                              'slave_host': 'localhost',
                                              'slave_port': 1234,
                                              'owner_id': str(self.user.id),
                                              'slave_token': '123'})
        with (yield from get_dummy_client(self.user)) as client:
            resp = yield from client.request2server(
                'repo-add-slave',
                {'repo_name_or_id': 'toxic/test-repo',
                 'slave_name_or_id': 'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_06_repo_remove_slave(self):
        with (yield from get_dummy_client(self.user)) as client:
            resp = yield from client.request2server(
                'repo-remove-slave',
                {'repo_name_or_id': 'toxic/test-repo',
                 'slave_name_or_id': 'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_07_slave_get(self):
        with (yield from get_dummy_client(self.user)) as client:
            resp = yield from client.request2server('slave-get',
                                                    {'slave_name_or_id':
                                                     'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_08_repo_get(self):
        with (yield from get_dummy_client(self.user)) as client:
            resp = yield from client.request2server('repo-get',
                                                    {'repo_name_or_id':
                                                     'toxic/test-repo'})
        self.assertTrue(resp)

    @async_test
    def test_09_slave_remove(self):
        with (yield from get_dummy_client(self.user)) as client:
            resp = yield from client.request2server('slave-remove',
                                                    {'slave_name_or_id':
                                                     'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_10_repo_start_build(self):
        # we need to wait so we have time to clone and create revs
        with (yield from get_dummy_client(self.user)) as client:
            yield from client.start_build()

        with (yield from get_dummy_client(self.user)) as client:
            yield from client.write({'action': 'stream', 'token': '123',
                                     'body': {},
                                     'user_id': str(self.user.id)})

            # this ugly part here it to wait for the right message
            # If we don't use this we may read the wrong message and
            # the test will fail.
            while True:
                response = yield from client.get_response()
                body = response['body'] if response else {}
                if body.get('event_type') == 'build_finished':
                    has_sleep = False
                    for step in body['steps']:
                        if step['command'] == 'sleep 3':
                            has_sleep = True

                    if not has_sleep:
                        break

        def get_bad_step(body):
            for step in body['steps']:
                if step['status'] == body['status']:
                    return step

        self.assertTrue(response['body']['finished'])

    @async_test
    def test_11_stream_step_output(self):

        with (yield from get_dummy_client(self.user)) as client:
            yield from client.write({'action': 'stream', 'token': '123',
                                     'body': {},
                                     'user_id': str(self.user.id)})

            with (yield from get_dummy_client(self.user)) as bclient:
                yield from bclient.start_build()

            steps = []
            # this ugly part here it to wait for the right message
            # If we don't use this we may read the wrong message and
            # the test will fail.

            while True:
                response = yield from client.get_response()
                body = response['body'] if response else {}
                if body.get('event_type') == 'step_output_info':
                    steps.append(body)

                if steps:
                    break

        self.assertTrue(steps)

    @async_test
    async def test_12_add_user(self):
        with (await get_dummy_client(self.user)) as client:
            r = await client.create_user()
        self.assertTrue(r['id'])

    @async_test
    async def test_13_user_authenticate(self):

        with (await get_dummy_client(self.user)) as client:
            r = await client.user_authenticate()
        self.assertTrue(r['id'])

    @async_test
    async def test_14_user_remove(self):
        with (await get_dummy_client(self.user)) as client:
            r = await client.remove_user()
        self.assertEqual(r, 'ok')

    @classmethod
    @asyncio.coroutine
    def _delete_test_data(cls):
        with (yield from get_dummy_client(cls.user)) as client:
            yield from client.request2server('slave-remove',
                                             {'slave_name_or_id':
                                              'toxic/test-slave'})
            yield from client.connect()
            yield from client.request2server('repo-remove',
                                             {'repo_name_or_id':
                                              'toxic/test-repo'})
