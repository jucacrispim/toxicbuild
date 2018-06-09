# -*- coding: utf-8 -*-

# Copyright 2015, 2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest import mock, TestCase
from toxicbuild.core.utils import now
from toxicbuild.master import client, build, repository, slave, users
from tests import async_test, AsyncMagicMock


class BuildClientTest(TestCase):

    @async_test
    async def setUp(self):
        super().setUp()

        addr, port = '127.0.0.1', 7777
        slave = mock.Mock()
        self.owner = users.User(email='a@a.com', password='asdf')
        await self.owner.save()
        self.client = client.BuildClient(slave, addr, port)

    @async_test
    async def tearDown(self):
        await build.BuildSet.drop_collection()
        await repository.Repository.drop_collection()
        await slave.Slave.drop_collection()
        await build.Builder.drop_collection()
        await users.User.drop_collection()

    @async_test
    async def test_healthcheck_not_alive(self):
        self.client.write = mock.MagicMock(side_effect=Exception)

        isalive = await self.client.healthcheck()

        self.assertFalse(isalive)

    @async_test
    async def test_healthcheck_alive(self):
        write = mock.MagicMock()
        self.client.write = asyncio.coroutine(lambda *a, **kw: write(*a, **kw))

        @asyncio.coroutine
        def gr(*a, **kw):
            return 1

        self.client.get_response = gr
        isalive = await self.client.healthcheck()

        self.assertTrue(isalive)

    @async_test
    async def test_list_builders(self):
        write = mock.MagicMock()
        self.client.write = asyncio.coroutine(lambda *a, **kw: write(*a, **kw))

        @asyncio.coroutine
        def gr():
            return {'code': 0,
                    'body': {'builders': ['b1', 'b2']}}

        self.client.get_response = gr

        expected = ['b1', 'b2']

        builders = await self.client.list_builders(
            'repourl', 'vcs_type', 'branch', 'named_tree')

        self.assertEqual(expected, builders)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_build(self):
        write = mock.MagicMock()
        self.client.write = asyncio.coroutine(lambda *a, **kw: write(*a, **kw))

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

        async def gr():
            # I need this sleep here so I can test the exact
            # behavior of the get_response method. No, it does not
            # sleep, but pass the control to the select thing.
            await asyncio.sleep(0.001)
            self.GR_COUNT += 1
            return self.GR_RETURNS[self.GR_COUNT]

        self.client.get_response = gr

        slave_inst = slave.Slave(name='slv', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await slave_inst.save()
        process = mock.Mock()

        process_coro = asyncio.coroutine(lambda build, build_info: process())

        repo = repository.Repository(name='repo', url='git@somewhere.com',
                                     slaves=[slave_inst], update_seconds=300,
                                     vcs_type='git', owner=self.owner)
        await repo.save()
        revision = repository.RepositoryRevision(
            commit='sdafj', repository=repo, branch='master', commit_date=now,
            author='ze', title='huehue')

        await revision.save()
        builder = build.Builder(repository=repo, name='b1')
        await builder.save()

        buildinstance = build.Build(repository=repo, slave=slave_inst,
                                    builder=builder, branch='master',
                                    named_tree='123sdf09')
        buildset = await build.BuildSet.create(repository=repo,
                                               revision=revision)

        await buildset.save()

        await self.client.build(buildinstance, process_coro=process_coro)
        self.assertEqual(len(process.call_args_list), 3)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_build_without_out_fn(self):
        write = mock.MagicMock()
        self.client.write = asyncio.coroutine(lambda *a, **kw: write(*a, **kw))

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

        async def gr():
            # I need this sleep here so I can test the exact
            # behavior of the get_response method. No, it does not
            # sleep, but pass the control to the select thing.
            await asyncio.sleep(0.001)
            self.GR_COUNT += 1
            return self.GR_RETURNS[self.GR_COUNT]

        self.client.get_response = gr

        slave_inst = slave.Slave(name='slv', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await slave_inst.save()
        process = mock.Mock()

        repo = repository.Repository(name='repo', url='git@somewhere.com',
                                     slaves=[slave_inst], update_seconds=300,
                                     vcs_type='git', owner=self.owner)
        await repo.save()
        revision = repository.RepositoryRevision(
            commit='sdafj', repository=repo, branch='master', commit_date=now,
            author='ze', title='huehue')

        await revision.save()
        builder = build.Builder(repository=repo, name='b1')
        await builder.save()

        buildinstance = build.Build(repository=repo, slave=slave_inst,
                                    builder=builder, branch='master',
                                    named_tree='123sdf09')
        buildset = await build.BuildSet.create(repository=repo,
                                               revision=revision)

        await buildset.save()

        await self.client.build(buildinstance, process_coro=None)
        self.assertEqual(len(process.call_args_list), 0)

    @mock.patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_build_without_out_fn_external(self):
        write = mock.MagicMock()
        self.client.write = asyncio.coroutine(lambda *a, **kw: write(*a, **kw))

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
            {'code': 0,
             'body': None},
            {},
        ]

        async def gr():
            # I need this sleep here so I can test the exact
            # behavior of the get_response method. No, it does not
            # sleep, but pass the control to the select thing.
            await asyncio.sleep(0.001)
            self.GR_COUNT += 1
            return self.GR_RETURNS[self.GR_COUNT]

        self.client.get_response = gr

        slave_inst = slave.Slave(name='slv', host='localhost', port=1234,
                                 token='123', owner=self.owner)
        await slave_inst.save()
        process = mock.Mock()

        repo = repository.Repository(name='repo', url='git@somewhere.com',
                                     slaves=[slave_inst], update_seconds=300,
                                     vcs_type='git', owner=self.owner)
        await repo.save()
        revision = repository.RepositoryRevision(
            commit='sdafj', repository=repo, branch='master', commit_date=now,
            author='ze', title='huehue')

        await revision.save()
        builder = build.Builder(repository=repo, name='b1')
        await builder.save()

        external = build.ExternalRevisionIinfo(url='http://bla.com/bla.git',
                                               name='remote', branch='master',
                                               into='into')
        buildinstance = build.Build(repository=repo, slave=slave_inst,
                                    builder=builder, branch='master',
                                    named_tree='123sdf09', external=external)
        buildset = await build.BuildSet.create(repository=repo,
                                               revision=revision)

        await buildset.save()

        await self.client.build(buildinstance, process_coro=None)
        self.assertEqual(len(process.call_args_list), 0)

    @mock.patch.object(client.BuildClient, 'connect', AsyncMagicMock(
        spec=client.BuildClient.connect))
    @async_test
    async def test_get_build_client(self):

        slave = mock.Mock()
        inst = await client.get_build_client(slave, 'localhost', 7777)

        self.assertTrue(inst.connect.called)
