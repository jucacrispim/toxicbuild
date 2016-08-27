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
from toxicbuild.core import BaseToxicClient
from toxicbuild.master.scheduler import scheduler
from toxicbuild.master import settings
from tests import async_test
from tests.functional import BaseFunctionalTest, REPO_DIR


scheduler.stop()


class DummyUIClient(BaseToxicClient):

    @asyncio.coroutine
    def request2server(self, action, body):

        data = {'action': action, 'body': body,
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
                'slave_token': '123'}

        resp = yield from self.request2server(action, body)
        return resp

    @asyncio.coroutine
    def create_repo(self):
        action = 'repo-add'
        body = {'repo_name': 'test-repo', 'repo_url': REPO_DIR,
                'vcs_type': 'git', 'update_seconds': 1,
                'slaves': ['test-slave']}

        resp = yield from self.request2server(action, body)

        return resp

    @asyncio.coroutine
    def start_build(self):

        action = 'repo-start-build'
        body = {'repo_name': 'test-repo',
                # 'builder_name': 'test-builder',
                'branch': 'master'}
        resp = yield from self.request2server(action, body)

        return resp

    def get_stream(self):

        action = 'stream'
        self.write({'action': action, 'body': {}})

        resp = yield from self.get_response()
        while resp:
            yield resp
            resp = yield from self.get_response()


@asyncio.coroutine
def get_dummy_client():
    dc = DummyUIClient(settings.HOLE_ADDR, settings.HOLE_PORT)
    yield from dc.connect()
    return dc


class ToxicMasterTest(BaseFunctionalTest):

    @classmethod
    def tearDownClass(cls):
        try:
            cls._delete_test_data()
        except OSError:
            pass

        super().tearDownClass()

    @async_test
    def test_01_create_slave(self):

        with (yield from get_dummy_client()) as client:
            response = yield from client.create_slave()
        self.assertTrue(response)

    @async_test
    def test_02_list_slaves(self):
        with (yield from get_dummy_client()) as client:
            slaves = yield from client.request2server('slave-list', {})

        self.assertEqual(len(slaves), 1)

    @async_test
    def test_03_create_repo(self):
        with (yield from get_dummy_client()) as client:
            response = yield from client.create_repo()

        self.assertTrue(response)

    @async_test
    def test_04_list_repos(self):
        with (yield from get_dummy_client()) as client:
            repos = yield from client.request2server('repo-list', {})

        self.assertEqual(len(repos), 1)
        self.assertEqual(len(repos[0]['slaves']), 1)

    @async_test
    def test_05_repo_add_slave(self):
        with (yield from get_dummy_client()) as client:
            yield from client.request2server('slave-add',
                                             {'slave_name': 'test-slave2',
                                              'slave_host': 'localhost',
                                              'slave_port': 1234,
                                              'slave_token': '123'})
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server(
                'repo-add-slave',
                {'repo_name': 'test-repo', 'slave_name': 'test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_06_repo_remove_slave(self):
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server(
                'repo-remove-slave',
                {'repo_name': 'test-repo', 'slave_name': 'test-slave'})
        self.assertTrue(resp)

    @async_test
    def test_07_slave_get(self):
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server('slave-get',
                                                    {'slave_name':
                                                     'test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_08_repo_get(self):
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server('repo-get',
                                                    {'repo_name':
                                                     'test-repo'})
        self.assertTrue(resp)

    @async_test
    def test_09_slave_remove(self):
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server('slave-remove',
                                                    {'slave_name':
                                                     'test-slave2'})
        self.assertTrue(resp)

    @async_test
    def test_10_repo_start_build(self):
        # we need to wait so we have time to clone and create revs
        yield from asyncio.sleep(1)
        with (yield from get_dummy_client()) as client:
            yield from client.start_build()

        with (yield from get_dummy_client()) as client:
            yield from client.write({'action': 'stream', 'token': '123',
                                     'body': {}})


            while True:
                response = yield from client.get_response()
                body = response['body'] if response else {}
                if 'steps' not in body and body.get('finished'):
                    break

        self.assertEqual(response['body']['status'], 'success')

    @classmethod
    def _delete_test_data(cls):
        loop = asyncio.get_event_loop()
        with loop.run_until_complete(get_dummy_client()) as client:
            loop.run_until_complete(
                client.request2server('slave-remove',
                                      {'slave_name': 'test-slave'}))

            loop.run_until_complete(client.connect())

            loop.run_until_complete(
                client.request2server('repo-remove',
                                      {'repo_name': 'test-repo'}))
