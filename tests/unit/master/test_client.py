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
import json
from unittest import mock
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.master import client


class BuildClientTest(AsyncTestCase):

    def setUp(self):
        super().setUp()

        addr, port = '127.0.0.1', 7777
        self.client = client.BuildClient(addr, port)

    @gen_test
    def test_healthcheck_not_alive(self):
        self.client.write = mock.Mock(side_effect=Exception)

        isalive = yield from self.client.healthcheck()

        self.assertFalse(isalive)

    @gen_test
    def test_healthcheck_alive(self):
        self.client.write = mock.Mock()

        @asyncio.coroutine
        def gr(*a, **kw):
            return 1

        self.client.get_response = gr

        isalive = yield from self.client.healthcheck()

        self.assertTrue(isalive)

    @gen_test
    def test_list_builders(self):
        self.client.write = mock.Mock()

        @asyncio.coroutine
        def gr():
            return {'code': 0,
                    'body': {'builders': ['b1', 'b2']}}

        self.client.get_response = gr

        expected = ['b1', 'b2']

        builders = yield from self.client.list_builders(
            'repourl', 'vcs_type', 'branch', 'named_tree')

        self.assertEqual(expected, builders)

    @gen_test
    def test_build(self):
        self.client.write = mock.Mock()

        self.GR_COUNT = -1

        self.GR_RETURNS = [
            {'code': 0,
             'body': {'status': 'running',
                      'cmd': 'ls', 'name': 'run ls',
                      'output': ''}},

            {'code': 0,
             'body': {'status': 'success',
                      'cmd': 'ls', 'name': 'run ls',
                      'output': 'somefile.txt\n'}},

            {'code': 0,
             'body': {'status': 'success', 'total_steps': 1,
                      'steps': {'cmd': 'ls', 'status': 'success',
                                'name': 'run ls',
                                'output': 'somefile.txt\n'}}},
            {},
        ]

        @asyncio.coroutine
        def gr():
            self.GR_COUNT += 1
            return self.GR_RETURNS[self.GR_COUNT]

        self.client.get_response = gr

        for build_info in self.client.build('repo_url', 'vcs_type', 'branch',
                                            'named_tree', 'builder_name'):

            self.assertEqual(build_info,
                             self.GR_RETURNS[self.GR_COUNT]['body'])

        self.assertEqual(self.GR_COUNT, 3)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @gen_test
    def test_get_build_client(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        inst = yield from client.get_build_client('localhost', 7777)

        self.assertTrue(inst._connected)
