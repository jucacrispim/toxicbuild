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
from unittest import mock
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core.utils import now
from toxicbuild.master import client, build, repository, slave


class BuildClientTest(AsyncTestCase):

    def setUp(self):
        super().setUp()

        addr, port = '127.0.0.1', 7777
        slave = mock.Mock()
        self.client = client.BuildClient(slave, addr, port)

    def tearDown(self):
        build.BuildSet.drop_collection()
        repository.Repository.drop_collection()
        slave.Slave.drop_collection()
        build.Builder.drop_collection()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_healthcheck_not_alive(self):
        self.client.write = mock.MagicMock(side_effect=Exception)

        isalive = yield from self.client.healthcheck()

        self.assertFalse(isalive)

    @gen_test
    def test_healthcheck_alive(self):
        self.client.write = mock.MagicMock()

        @asyncio.coroutine
        def gr(*a, **kw):
            return 1

        self.client.get_response = gr

        isalive = yield from self.client.healthcheck()

        self.assertTrue(isalive)

    @gen_test
    def test_list_builders(self):
        self.client.write = mock.MagicMock()

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
        self.client.write = mock.MagicMock()

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
            # I need this sleep here so I can test the exact
            # behavior of the get_response method. No, it does not
            # sleep, but pass the control to the select thing.
            yield from asyncio.sleep(0.001)
            self.GR_COUNT += 1
            return self.GR_RETURNS[self.GR_COUNT]

        self.client.get_response = gr

        slave_inst = slave.Slave(name='slv', host='localhost', port=1234)
        yield slave_inst.save()
        process = mock.Mock()

        self.client.slave._process_build_info = asyncio.coroutine(
            lambda build, build_info: process())

        repo = repository.Repository(name='repo', url='git@somewhere.com',
                                     slaves=[slave_inst], update_seconds=300,
                                     vcs_type='git')
        yield repo.save()
        revision = repository.RepositoryRevision(
            commit='sdafj', repository=repo, branch='master', commit_date=now)

        yield revision.save()
        builder = build.Builder(repository=repo, name='b1')
        yield builder.save()

        buildinstance = build.Build(repository=repo, slave=slave_inst,
                                    builder=builder, branch='master',
                                    named_tree='123sdf09')
        buildset = build.BuildSet(repository=repo, revision=revision,
                                  commit='asda',
                                  commit_date=now)
        yield buildset.save()

        yield from self.client.build(buildinstance)
        self.assertEqual(len(process.call_args_list), 3)

    @mock.patch.object(client.asyncio, 'open_connection', mock.MagicMock())
    @gen_test
    def test_get_build_client(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return mock.MagicMock(), mock.MagicMock()

        client.asyncio.open_connection = oc

        slave = mock.Mock()
        inst = yield from client.get_build_client(slave, 'localhost', 7777)

        self.assertTrue(inst._connected)
