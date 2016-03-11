# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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
import datetime
from unittest.mock import Mock, MagicMock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
import toxicbuild
from toxicbuild.core.utils import datetime2string
from toxicbuild.master import slave, build, repository


@patch.object(slave, 'build_started', Mock())
@patch.object(slave, 'build_finished', Mock())
@patch.object(slave, 'step_started', Mock())
@patch.object(slave, 'step_finished', Mock())
class SlaveTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.slave = slave.Slave(name='slave', host='127.0.0.1', port=7777)

    def tearDown(self):
        slave.Slave.drop_collection()
        build.Build.drop_collection()
        build.Builder.drop_collection()
        repository.RepositoryRevision.drop_collection()
        repository.Repository.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_create(self):
        slave_inst = yield from slave.Slave.create(name='name',
                                                   host='somewhere.net',
                                                   port=7777)
        self.assertTrue(slave_inst.id)

    @gen_test
    def test_get(self):
        slave_inst = yield from slave.Slave.create(name='name',
                                                   host='somewhere.net',
                                                   port=7777)
        slave_id = slave_inst.id

        slave_inst = yield from slave.Slave.get(name='name',
                                                host='somewhere.net',
                                                port=7777)

        self.assertEqual(slave_id, slave_inst.id)

    @patch.object(toxicbuild.master.client.asyncio, 'open_connection',
                  Mock())
    @gen_test
    def test_get_client(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return [MagicMock(), MagicMock()]

        toxicbuild.master.client.asyncio.open_connection = oc
        client = yield from self.slave.get_client()
        self.assertTrue(client._connected)

    @gen_test
    def test_healthcheck(self):

        @asyncio.coroutine
        def gc():
            client = MagicMock()

            @asyncio.coroutine
            def hc():  # x no pé!
                return True

            client.__enter__.return_value.healthcheck = hc
            return client

        self.slave.get_client = gc

        yield from self.slave.healthcheck()

        self.assertTrue(self.slave.is_alive)

    @gen_test
    def test_list_builders(self):
        yield from self._create_test_data()

        @asyncio.coroutine
        def gc():
            client = MagicMock()

            @asyncio.coroutine
            def lb(repo_url, vcs_type, branch, named_tree):
                return ['builder-1', 'builder-2']

            client.__enter__.return_value.list_builders = lb
            return client

        self.slave.get_client = gc

        builders = yield from self.slave.list_builders(self.revision)

        self.assertEqual(builders, [self.builder, self.other_builder])

    @gen_test
    def test_build(self):
        yield from self._create_test_data()
        client = MagicMock()

        @asyncio.coroutine
        def gc():

            @asyncio.coroutine
            def b(build):
                client.build()
                return []

            client.__enter__.return_value.build = b
            return client

        self.slave.get_client = gc
        future = yield from self.slave.build(self.build)
        yield from future
        self.assertTrue(client.build.called)

    @patch.object(slave, 'build_started', Mock())
    @gen_test
    def test_process_build_info_with_build_started(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime2string(datetime.datetime.now(tz=tz))

        build_info = {'status': 'running', 'steps': [],
                      'started': now, 'finished': None}

        yield from self.slave._process_build_info(self.build, build_info)
        self.assertTrue(slave.build_started.send.called)

    @patch.object(slave, 'build_finished', Mock())
    @gen_test
    def test_process_build_info_with_build_finished(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime2string(datetime.datetime.now(tz=tz))

        build_info = {'status': 'running', 'steps': [],
                      'started': now, 'finished': now}

        yield from self.slave._process_build_info(self.build, build_info)
        self.assertTrue(slave.build_finished.send.called)

    @gen_test
    def test_process_build_info_with_step(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)

        build_info = {'status': 'running', 'cmd': 'ls', 'name': 'ls',
                      'started': now, 'finished': None, 'output': ''}

        self.slave._set_step_info = MagicMock(
            spec=self.slave._set_step_info)
        yield from self.slave._process_build_info(self.build, build_info)
        self.assertTrue(self.slave._set_step_info.called)

    @gen_test
    def test_set_step_info_new(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)
        started = now.strftime('%a %b %d %H:%M:%S %Y %z')
        finished = now.strftime('%a %b %d %H:%M:%S %Y %z')

        yield from self.slave._set_step_info(self.build, 'ls', 'run ls',
                                             'running', '', started, finished)
        self.assertEqual(len(self.build.steps), 1)

    @gen_test
    def test_set_step_info(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)
        started = now.strftime('%a %b %d %H:%M:%S %Y %z')
        finished = now.strftime('%a %b %d %H:%M:%S %Y %z')

        yield from self.slave._set_step_info(self.build, 'ls', 'run ls',
                                             'running', '', started, finished)
        yield from self.slave._set_step_info(self.build, 'echo "oi"', 'echo',
                                             'running', '', started, finished)
        yield from self.slave._set_step_info(self.build, 'ls', 'run ls',
                                             'success', 'somefile.txt\n',
                                             started, finished)

        self.assertEqual(self.build.steps[0].status, 'success')
        self.assertEqual(len(self.build.steps), 2)

    @asyncio.coroutine
    def _create_test_data(self):
        yield self.slave.save()
        self.repo = repository.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        yield self.repo.save()

        self.revision = repository.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now()
        )

        yield self.revision.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        yield self.builder.save()
        self.other_builder = build.Builder(repository=self.repo,
                                           name='builder-2')
        yield self.other_builder.save()
        yield self.builder.save()

        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder, number=0)

        self.build.save()
