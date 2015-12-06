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
from tests.functional import REPO_DIR, SCRIPTS_DIR, SLAVE_ROOT_DIR, SOURCE_DIR


class DummyBuildClient(BaseToxicClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo_url = REPO_DIR

    @asyncio.coroutine
    def request2server(self, action, body):

        data = {'action': action, 'body': body}
        yield from self.write(data)

        response = yield from self.get_response()
        return response

    @asyncio.coroutine
    def is_server_alive(self):

        resp = yield from self.request2server('healthcheck', {})
        code = int(resp['code'])
        return code == 0

    @asyncio.coroutine
    def build(self, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': self.repo_url,
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master',
                         'builder_name': builder_name}}

        r = yield from self.request2server(data['action'], data['body'])

        build_resp = []
        while r:
            build_resp.append(r)
            r = yield from self.get_response()
            if not r:
                break

        steps, build_status = build_resp[1:-1], build_resp[-1]
        return steps, build_status

    @asyncio.coroutine
    def list_builders(self):
        data = {'action': 'list_builders',
                'body': {'repo_url': self.repo_url,
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master', }}

        r = yield from self.request2server(data['action'], data['body'])
        return r


@asyncio.coroutine
def get_dummy_client():
    dc = DummyBuildClient('localhost', 2222)
    yield from dc.connect()
    return dc


class SlaveTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @classmethod
    def setUpClass(cls):
        cls.toxicslave = os.path.join(SCRIPTS_DIR, 'toxicslave')
        start_cmd = 'export PYTHONPATH="{}" && {} start {} --daemonize'.format(
            SOURCE_DIR, cls.toxicslave, SLAVE_ROOT_DIR)
        cls.pidfile = os.path.join(SLAVE_ROOT_DIR, 'toxicslave.pid')
        os.system(start_cmd)

    @classmethod
    def tearDownClass(cls):
        with open(cls.pidfile, 'r') as fd:
            pid = int(fd.read())

        os.kill(pid, 9)
        os.remove(cls.pidfile)

    @gen_test
    def test_healthcheck(self):
        with (yield from get_dummy_client()) as client:
            is_alive = yield from client.is_server_alive()
            self.assertTrue(is_alive)

    @gen_test
    def test_list_builders(self):
        with (yield from get_dummy_client()) as client:
            builders = (yield from client.list_builders())['body']['builders']

        self.assertEqual(builders, ['builder-1', 'builder-2'], builders)

    @gen_test
    def test_build(self):
        with (yield from get_dummy_client()) as client:
            step_info, build_status = yield from client.build('builder-1')

        self.assertEqual(len(step_info), 2)
        self.assertEqual(build_status['body']['total_steps'], 1)
        self.assertEqual(build_status['body']['status'], 'success')

    @gen_test(timeout=15)
    def test_build_with_plugin(self):
        with (yield from get_dummy_client()) as client:
            step_info, build_status = yield from client.build('builder-2')

        self.assertEqual(len(step_info), 6)
        self.assertEqual(build_status['body']['total_steps'], 3)
        self.assertEqual(build_status['body']['status'], 'success')
        self.assertIn('3.4', build_status['body']['steps'][-1]['output'])
