# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from toxicbuild.core import BaseToxicClient
from toxicbuild.slave import settings
from tests import async_test
from tests.functional import REPO_DIR, BaseFunctionalTest


class DummyBuildClient(BaseToxicClient):

    def __init__(self, *args, **kwargs):
        kwargs['use_ssl'] = True
        kwargs['validate_cert'] = False
        super().__init__(*args, **kwargs)
        self.repo_url = REPO_DIR

    @asyncio.coroutine
    def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'token': '123'}
        yield from self.write(data)

        response = yield from self.get_response()
        return response

    @asyncio.coroutine
    def is_server_alive(self):

        resp = yield from self.request2server('healthcheck', {'bla': 1})
        code = int(resp['code'])
        return code == 0

    @asyncio.coroutine
    def build(self, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': self.repo_url,
                         'repo_id': 'repo_id',
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master',
                         'builder_name': builder_name}}

        r = yield from self.request2server(data['action'], data['body'])

        build_resp = []
        while r:
            if r.get('body').get('info_type') != 'step_output_info':
                build_resp.append(r)

            r = yield from self.get_response()
            if not r:
                break

        steps, build_status = build_resp[1:-1], build_resp[-1]
        return steps, build_status

    @asyncio.coroutine
    def build_output_info(self, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': self.repo_url,
                         'repo_id': 'repo_id',
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master',
                         'builder_name': builder_name}}

        r = yield from self.request2server(data['action'], data['body'])
        build_resp = []
        while r:
            if r.get('body').get('info_type') == 'step_output_info':
                build_resp.append(r)

            r = yield from self.get_response()
            if not r:
                break

        return build_resp

    @asyncio.coroutine
    def list_builders(self):
        data = {'action': 'list_builders',
                'body': {'repo_url': self.repo_url,
                         'repo_id': 'repo_id',
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master', }}

        r = yield from self.request2server(data['action'], data['body'])
        return r


@asyncio.coroutine
def get_dummy_client():
    dc = DummyBuildClient(settings.ADDR, settings.PORT)
    yield from dc.connect()
    return dc


class SlaveTest(BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        cls.start_slave()

    @classmethod
    def tearDownClass(cls):
        cls.stop_slave()

    @async_test
    def test_healthcheck(self):
        with (yield from get_dummy_client()) as client:
            is_alive = yield from client.is_server_alive()
            self.assertTrue(is_alive)

    @async_test
    def test_list_builders(self):
        with (yield from get_dummy_client()) as client:
            builders = (yield from client.list_builders())['body']['builders']

        self.assertEqual(builders, ['builder-1', 'builder-2', 'builder-3'],
                         builders)

    @async_test
    def test_build(self):
        with (yield from get_dummy_client()) as client:
            step_info, build_status = yield from client.build('builder-1')

        self.assertEqual(len(step_info), 2)
        self.assertEqual(build_status['body']['total_steps'], 1)
        self.assertEqual(build_status['body']['status'], 'success')

    @async_test
    def test_build_with_plugin(self):
        with (yield from get_dummy_client()) as client:
            step_info, build_status = yield from client.build('builder-2')

        self.assertEqual(step_info[0]['body']['name'], 'Create virtualenv')

    @async_test
    def test_buid_with_timeout_step(self):
        with (yield from get_dummy_client()) as client:
            step_info, build_status = yield from client.build('builder-3')

        self.assertEqual(build_status['body']['status'], 'exception')

    @async_test
    def test_step_output_info(self):
        with (yield from get_dummy_client()) as client:
            output_info = yield from client.build_output_info('builder-2')

        self.assertTrue(output_info)
