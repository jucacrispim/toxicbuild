# -*- coding: utf-8 -*-

# Copyright 2015-2020, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest.mock import patch, Mock
from toxicbuild.common.exchanges import scheduler_action, conn
from toxicbuild.master import settings
from toxicbuild.master.repository import Repository
from toxicbuild.master.slave import Slave
from toxicbuild.master.users import User
from tests import async_test
from tests.functional import (BaseFunctionalTest, DummyMasterHoleClient,
                              STREAM_EVENT_TYPES)


class DummyUIClient(DummyMasterHoleClient):

    async def create_slave(self):
        slave_port = settings.SLAVE_PORT
        r = await super().create_slave(slave_port)
        return r

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

    async def get_stream(self):

        action = 'stream'
        self.write({'action': action,
                    'body': {'event_types': STREAM_EVENT_TYPES}})

        resp = await self.get_response()
        while resp:
            yield resp
            resp = await self.get_response()

    async def wait_clone(self):
        await self.write({'action': 'stream', 'token': '123',
                          'body': {'event_types': STREAM_EVENT_TYPES},
                          'user_id': str(self.user.id)})
        while True:
            r = await self.get_response()
            body = r['body'] if r else {}
            try:
                event = body['event_type']
                if event == 'repo_status_changed':
                    break
            except KeyError:
                pass

    async def enable_plugin(self):
        action = 'repo-enable-plugin'
        body = {'repo_name_or_id': 'toxic/test-repo',
                'plugin_name': 'custom-webhook',
                'webhook_url': 'http://localhost:{}/webhookmessage/'.format(
                    settings.WEBHOOK_PORT),
                'branches': ['master'],
                'statuses': ['running', 'fail', 'success']}

        resp = await self.request2server(action, body)
        return resp

    async def disable_plugin(self):
        action = 'repo-disable-plugin'
        body = {'repo_name_or_id': 'toxic/test-repo',
                'plugin_name': 'slack-notification'}

        resp = await self.request2server(action, body)
        return resp


async def get_dummy_client(user):
    dc = DummyUIClient(user, settings.HOLE_ADDR, settings.HOLE_PORT)
    await dc.connect()
    return dc


class ToxicMasterTest(BaseFunctionalTest):

    @classmethod
    @async_test
    async def setUpClass(cls):
        super().setUpClass()
        await User.objects.all().delete()
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
        await conn.connect(**settings.RABBITMQ_CONNECTION)
        await scheduler_action.declare()
        await scheduler_action.queue_delete()
        await scheduler_action.connection.disconnect()
        super().tearDownClass()
        await Slave.drop_collection()

    @async_test
    async def tearDown(self):
        await Repository.objects(name__not__exists=1).delete()
        await Repository.objects(name=None).delete()
        await Repository.objects(url=None).delete()

    @async_test
    async def test_01_create_slave(self):
        with (await get_dummy_client(self.user)) as client:
            response = await client.create_slave()
        self.assertTrue(response)

    @async_test
    async def test_02_list_slaves(self):
        with (await get_dummy_client(self.user)) as client:
            slaves = await client.request2server('slave-list', {})

        self.assertEqual(len(slaves), 1)

    @async_test
    async def test_03_create_repo(self):
        with (await get_dummy_client(self.user)) as client:
            response = await client.create_repo()

        with (await get_dummy_client(self.user)) as client:
            await client.wait_clone()

        with (await get_dummy_client(self.user)) as client:
            await client.wait_build_complete()

        self.assertTrue(response)

    @async_test
    async def test_04_list_repos(self):
        with (await get_dummy_client(self.user)) as client:
            repos = await client.request2server('repo-list', {})

        self.assertEqual(len(repos), 1)
        self.assertTrue(repos[0]['url'])

    @async_test
    async def test_05_repo_add_slave(self):
        with (await get_dummy_client(self.user)) as client:
            await client.request2server('slave-add',
                                        {'slave_name': 'test-slave2',
                                         'slave_host': 'localhost',
                                         'slave_port': 1234,
                                         'owner_id': str(self.user.id),
                                         'slave_token': '123'})
        with (await get_dummy_client(self.user)) as client:
            resp = await client.request2server(
                'repo-add-slave',
                {'repo_name_or_id': 'toxic/test-repo',
                 'slave_name_or_id': 'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    async def test_06_repo_remove_slave(self):
        with (await get_dummy_client(self.user)) as client:
            resp = await client.request2server(
                'repo-remove-slave',
                {'repo_name_or_id': 'toxic/test-repo',
                 'slave_name_or_id': 'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    async def test_07_slave_get(self):
        with (await get_dummy_client(self.user)) as client:
            resp = await client.request2server('slave-get',
                                               {'slave_name_or_id':
                                                'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    async def test_08_repo_get(self):
        with (await get_dummy_client(self.user)) as client:
            resp = await client.request2server('repo-get',
                                               {'repo_name_or_id':
                                                'toxic/test-repo'})
        self.assertTrue(resp)

    @async_test
    async def test_09_slave_remove(self):
        with (await get_dummy_client(self.user)) as client:
            resp = await client.request2server('slave-remove',
                                               {'slave_name_or_id':
                                                'toxic/test-slave2'})
        self.assertTrue(resp)

    @async_test
    async def test_10_repo_start_build(self):
        # we need to wait so we have time to clone and create revs
        with (await get_dummy_client(self.user)) as client:
            await client.start_build()

        with (await get_dummy_client(self.user)) as client:
            response = await client.wait_build_complete()

        self.assertTrue(response['body']['finished'])

    @async_test
    async def test_11_stream_step_output(self):

        with (await get_dummy_client(self.user)) as client:
            await client.write({
                'action': 'stream', 'token': '123',
                'body': {'event_types': STREAM_EVENT_TYPES},
                'user_id': str(self.user.id)})

            with (await get_dummy_client(self.user)) as bclient:
                await bclient.start_build()

            steps = []
            # this ugly part here it to wait for the right message
            # If we don't use this we may read the wrong message and
            # the test will fail.

            while True:
                response = await client.get_response()
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

    @async_test
    async def test_15_waterfall_get(self):
        data = {'repo_name_or_id': 'toxic/test-repo'}
        with (await get_dummy_client(self.user)) as client:
            resp = await client.request2server('waterfall-get', data)
        self.assertTrue(resp)
        self.assertTrue(resp['buildsets'])
        self.assertTrue(resp['builders'])
        self.assertTrue(resp['branches'])

    @classmethod
    async def _delete_test_data(cls):
        with (await get_dummy_client(cls.user)) as client:
            await client.request2server('slave-remove',
                                        {'slave_name_or_id':
                                         'toxic/test-slave'})
            await client.connect()
            await client.request2server('repo-remove',
                                        {'repo_name_or_id':
                                         'toxic/test-repo'})
