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

    async def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'token': '123'}
        await self.write(data)

        response = await self.get_response()
        return response

    async def is_server_alive(self):

        resp = await self.request2server('healthcheck', {'bla': 1})
        code = int(resp['code'])
        return code == 0

    async def build(self, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': self.repo_url,
                         'repo_id': 'repo_id',
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master',
                         'builder_name': builder_name}}

        r = await self.request2server(data['action'], data['body'])

        build_resp = []
        while r:
            if r.get('body').get('info_type') != 'step_output_info':
                build_resp.append(r)

            r = await self.get_response()
            if not r:
                break

        steps, build_status = build_resp[1:-1], build_resp[-1]
        return steps, build_status

    async def build_output_info(self, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': self.repo_url,
                         'repo_id': 'repo_id',
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master',
                         'builder_name': builder_name}}

        r = await self.request2server(data['action'], data['body'])
        build_resp = []
        while r:
            if r.get('body').get('info_type') == 'step_output_info':
                build_resp.append(r)

            r = await self.get_response()
            if not r:
                break

        return build_resp

    async def list_builders(self):
        data = {'action': 'list_builders',
                'body': {'repo_url': self.repo_url,
                         'repo_id': 'repo_id',
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master', }}

        r = await self.request2server(data['action'], data['body'])
        return r


async def get_dummy_client():
    dc = DummyBuildClient(settings.ADDR, settings.PORT)
    await dc.connect()
    return dc


class SlaveTest(BaseFunctionalTest):

    @classmethod
    def setUpClass(cls):
        cls.start_slave()

    @classmethod
    def tearDownClass(cls):
        cls.stop_slave()

    @async_test
    async def test_healthcheck(self):
        with (await get_dummy_client()) as client:
            is_alive = await client.is_server_alive()
            self.assertTrue(is_alive)

    @async_test
    async def test_list_builders(self):
        with (await get_dummy_client()) as client:
            builders = (await client.list_builders())['body']['builders']

        self.assertEqual(builders, ['builder-1', 'builder-2', 'builder-3'],
                         builders)

    @async_test
    async def test_build(self):
        with (await get_dummy_client()) as client:
            step_info, build_status = await client.build('builder-1')

        self.assertEqual(len(step_info), 2)
        self.assertEqual(build_status['body']['total_steps'], 1)
        self.assertEqual(build_status['body']['status'], 'success')

    @async_test
    async def test_build_with_plugin(self):
        with (await get_dummy_client()) as client:
            step_info, build_status = await client.build('builder-2')

        self.assertEqual(step_info[0]['body']['name'], 'Create virtualenv')

    @async_test
    async def test_buid_with_timeout_step(self):
        with (await get_dummy_client()) as client:
            step_info, build_status = await client.build('builder-3')

        self.assertEqual(build_status['body']['status'], 'exception')

    @async_test
    async def test_step_output_info(self):
        with (await get_dummy_client()) as client:
            output_info = await client.build_output_info('builder-2')

        self.assertTrue(output_info)
