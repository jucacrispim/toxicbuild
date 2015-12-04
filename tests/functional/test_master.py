# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
import os
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core import BaseToxicClient
from toxicbuild.master.scheduler import scheduler
from tests.functional import (SCRIPTS_DIR, REPO_DIR, SOURCE_DIR,
                              MASTER_ROOT_DIR, SLAVE_ROOT_DIR)


scheduler.stop()


class DummyUIClient(BaseToxicClient):

    @asyncio.coroutine
    def request2server(self, action, body):

        data = {'action': action, 'body': body}
        yield from self.write(data)
        response = yield from self.get_response()
        return response['body'][action]

    @asyncio.coroutine
    def create_slave(self):
        action = 'slave-add'
        body = {'slave_name': 'test-slave',
                'slave_host': 'localhost',
                'slave_port': 7777}

        resp = yield from self.request2server(action, body)
        return resp

    @asyncio.coroutine
    def create_repo(self):
        action = 'repo-add'
        body = {'repo_name': 'test-repo', 'repo_url': REPO_DIR,
                'vcs_type': 'git', 'update_seconds': 300,
                'slaves': ['test-slave']}

        resp = yield from self.request2server(action, body)

        return resp

    @asyncio.coroutine
    def start_build(self):

        action = 'builder-start-build'
        body = {'repo_name': 'test-repo',
                'builder_name': 'test-builder',
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
    dc = DummyUIClient('localhost', 1111)
    yield from dc.connect()
    return dc


class ToxicMasterTest(AsyncTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._loop = asyncio.get_event_loop()
        cls._ruc = cls._loop.run_until_complete

        # start slave
        toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
               toxicslave_cmd, 'start', SLAVE_ROOT_DIR, '--daemonize']

        os.system(' '.join(cmd))

        # start master
        toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
               toxicmaster_cmd, 'start', MASTER_ROOT_DIR, '--daemonize']

        os.system(' '.join(cmd))

    @classmethod
    def tearDownClass(cls):
        try:
            cls._delete_test_data()
        except OSError:
            pass

        # stop slave
        toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
               'python', toxicslave_cmd, 'stop', SLAVE_ROOT_DIR]

        os.system(' '.join(cmd))

        # stop master
        toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
               'python', toxicmaster_cmd, 'stop', MASTER_ROOT_DIR]
        os.system(' '.join(cmd))

        super().tearDownClass()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_1_create_slave(self):

        with (yield from get_dummy_client()) as client:
            response = yield from client.create_slave()
        self.assertTrue(response)

    @gen_test
    def test_2_list_slaves(self):
        with (yield from get_dummy_client()) as client:
            slaves = yield from client.request2server('slave-list', {})

        self.assertEqual(len(slaves), 1)

    @gen_test
    def test_3_create_repo(self):
        with (yield from get_dummy_client()) as client:
            response = yield from client.create_repo()

        self.assertTrue(response)

    @gen_test
    def test_4_list_repos(self):
        with (yield from get_dummy_client()) as client:
            repos = yield from client.request2server('repo-list', {})

        self.assertEqual(len(repos), 1)
        self.assertEqual(len(repos[0]['slaves']), 1)

    @gen_test
    def test_5_repo_add_slave(self):
        with (yield from get_dummy_client()) as client:
            yield from client.request2server('slave-add',
                                             {'slave_name': 'test-slave2',
                                              'slave_host': 'localhost',
                                              'slave_port': 1234})
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server(
                'repo-add-slave',
                {'repo_name': 'test-repo', 'slave_name': 'test-slave2'})
        self.assertTrue(resp)

    @gen_test
    def test_6_repo_remove_slave(self):
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server(
                'repo-remove-slave',
                {'repo_name': 'test-repo', 'slave_name': 'test-slave'})
        self.assertTrue(resp)

    @gen_test
    def test_7_slave_remove(self):
        with (yield from get_dummy_client()) as client:
            resp = yield from client.request2server('slave-remove',
                                                    {'slave_name':
                                                     'test-slave2'})
        self.assertTrue(resp)

    # @gen_test
    # def test_8_start_build(self):
    #     pass

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
