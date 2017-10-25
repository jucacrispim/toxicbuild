# -*- coding: utf-8 -*-

# Copyright 2016-2017 Juca Crispim <juca@poraodojuca.net>

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
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
import toxicbuild
from toxicbuild.core.utils import datetime2string
from toxicbuild.master import slave, build, repository
from tests import async_test


@patch.object(slave, 'build_started', Mock())
@patch.object(slave, 'build_finished', Mock())
@patch.object(slave, 'step_started', Mock())
@patch.object(slave, 'step_finished', Mock())
@patch.object(slave, 'step_output_arrived', Mock())
class SlaveTest(TestCase):

    def setUp(self):
        super().setUp()
        self.slave = slave.Slave(name='slave', host='127.0.0.1', port=7777,
                                 token='asdf')

    @async_test
    def tearDown(self):
        yield from slave.Slave.drop_collection()
        yield from build.BuildSet.drop_collection()
        yield from build.Builder.drop_collection()
        yield from repository.RepositoryRevision.drop_collection()
        yield from repository.Repository.drop_collection()
        super().tearDown()

    @async_test
    def test_create(self):
        slave_inst = yield from slave.Slave.create(name='name',
                                                   host='somewhere.net',
                                                   port=7777,
                                                   token='asdf')
        self.assertTrue(slave_inst.id)

    @async_test
    def test_to_dict(self):
        slave_inst = yield from slave.Slave.create(name='name',
                                                   host='somewhere.net',
                                                   port=7777,
                                                   token='asdf')
        slave_dict = slave_inst.to_dict()
        self.assertTrue(slave_dict['id'])

    @async_test
    def test_to_dict_id_as_str(self):
        slave_inst = yield from slave.Slave.create(name='name',
                                                   host='somewhere.net',
                                                   port=7777,
                                                   token='asdf')
        slave_dict = slave_inst.to_dict(id_as_str=True)
        self.assertIsInstance(slave_dict['id'], str)

    @async_test
    def test_get(self):
        slave_inst = yield from slave.Slave.create(name='name',
                                                   host='somewhere.net',
                                                   port=7777,
                                                   token='asdf')
        slave_id = slave_inst.id

        slave_inst = yield from slave.Slave.get(name='name',
                                                host='somewhere.net',
                                                port=7777)

        self.assertEqual(slave_id, slave_inst.id)

    @patch.object(toxicbuild.master.client.asyncio, 'open_connection',
                  Mock())
    @async_test
    def test_get_client(self):

        @asyncio.coroutine
        def oc(*a, **kw):
            return [MagicMock(), MagicMock()]

        toxicbuild.master.client.asyncio.open_connection = oc
        client = yield from self.slave.get_client()
        self.assertTrue(client._connected)

    @async_test
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

    @async_test
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

    @async_test
    def test_build(self):
        yield from self._create_test_data()
        client = MagicMock()

        @asyncio.coroutine
        def gc():

            @asyncio.coroutine
            def b(build, process_coro):
                client.build()
                return []

            client.__enter__.return_value.build = b
            return client

        self.slave.get_client = gc
        yield from self.slave.build(self.build)
        self.assertTrue(client.build.called)

    @async_test
    def test_build_with_exception(self):
        yield from self._create_test_data()
        client = MagicMock()

        @asyncio.coroutine
        def gc():

            @asyncio.coroutine
            def b(build, process_coro):
                raise slave.ToxicClientException

            client.__enter__.return_value.build = b
            return client

        self.slave.get_client = gc
        build_info = yield from self.slave.build(self.build)
        self.assertEqual(self.build.status, 'exception')
        self.assertTrue(self.build.finished)
        self.assertEqual(len(build_info['steps']), 1)

    @patch.object(slave, 'build_started', Mock())
    @async_test
    def test_process_info_with_build_started(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime2string(datetime.datetime.now(tz=tz))

        build_info = {'status': 'running', 'steps': [],
                      'started': now, 'finished': None,
                      'info_type': 'build_info'}

        yield from self.slave._process_info(self.build, build_info)
        self.assertTrue(slave.build_started.send.called)

    @patch.object(slave, 'build_finished', Mock())
    @async_test
    def test_process_info_with_build_finished(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)
        formate_now = datetime2string(now)
        future_now = now + datetime.timedelta(seconds=2)
        future_formated_now = datetime2string(future_now)

        build_info = {'status': 'running', 'steps': [],
                      'started': formate_now, 'finished': future_formated_now,
                      'info_type': 'build_info',
                      'total_time': 2}

        yield from self.slave._process_info(self.build, build_info)
        self.assertTrue(slave.build_finished.send.called)

    @async_test
    def test_process_info_with_step(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)

        build_info = {'status': 'running', 'cmd': 'ls', 'name': 'ls',
                      'started': now, 'finished': None, 'output': '',
                      'index': 0, 'info_type': 'step_info'}

        self.slave._process_step_info = MagicMock(
            spec=self.slave._process_step_info)
        yield from self.slave._process_info(self.build, build_info)
        self.assertTrue(self.slave._process_step_info.called)

    @async_test
    def test_process_info_with_step_output(self):
        yield from self._create_test_data()
        info = {'info_type': 'step_output_info'}

        self.slave._process_step_output_info = MagicMock(
            spec=self.slave._process_step_output_info)

        yield from self.slave._process_info(self.build, info)
        self.assertTrue(self.slave._process_step_output_info.called)

    @async_test
    def test_process_step_info_new(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)
        started = now.strftime('%a %b %d %H:%M:%S %Y %z')
        finished = None

        step_info = {'status': 'running', 'cmd': 'ls', 'name': 'run ls',
                     'output': '', 'started': started, 'finished': finished,
                     'index': 0, 'uuid': uuid4()}
        yield from self.slave._process_step_info(self.build, step_info)
        self.assertEqual(len(self.build.steps), 1)

    @async_test
    def test_process_step_info(self):
        yield from self._create_test_data()
        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)
        started = now.strftime('%a %b %d %H:%M:%S %Y %z')
        finished = (now + datetime.timedelta(seconds=2)).strftime(
            '%a %b %d %H:%M:%S %Y %z')
        a_uuid = uuid4()
        other_uuid = uuid4()

        info = {'cmd': 'ls', 'name': 'run ls', 'status': 'running',
                'output': '', 'started': started, 'finished': None,
                'index': 0, 'uuid': a_uuid}

        yield from self.slave._process_step_info(self.build, info)

        info = {'cmd': 'echo "oi"', 'name': 'echo', 'status': 'success',
                'output': '', 'started': started, 'finished': finished,
                'index': 1, 'uuid': other_uuid}

        yield from self.slave._process_step_info(self.build, info)

        info = {'cmd': 'ls', 'name': 'run ls', 'status': 'success',
                'output': 'somefile.txt\n', 'started': started,
                'finished': finished,
                'index': 0, 'uuid': a_uuid}

        yield from self.slave._process_step_info(self.build, info)

        self.assertEqual(self.build.steps[0].status, 'success')
        self.assertEqual(len(self.build.steps), 2)
        self.assertTrue(self.build.steps[0].total_time)

    @async_test
    def test_process_step_output_info(self):
        yield from self._create_test_data()

        tz = datetime.timezone(-datetime.timedelta(hours=3))
        now = datetime.datetime.now(tz=tz)
        started = now.strftime('%a %b %d %H:%M:%S %Y %z')
        a_uuid = uuid4()

        info = {'cmd': 'ls', 'name': 'run ls', 'status': 'running',
                'output': '', 'started': started, 'finished': None,
                'index': 0, 'uuid': a_uuid}

        yield from self.slave._process_step_info(self.build, info)

        info = {'uuid': a_uuid, 'output': 'somefile.txt\n'}
        yield from self.slave._process_step_output_info(self.build, info)
        step = self.slave._get_step(self.build, a_uuid)
        self.assertTrue(step.output)

    @asyncio.coroutine
    def _create_test_data(self):
        yield from self.slave.save()
        self.repo = repository.Repository(
            name='reponame', url='git@somewhere', update_seconds=300,
            vcs_type='git', slaves=[self.slave])

        yield from self.repo.save()

        self.revision = repository.RepositoryRevision(
            repository=self.repo, branch='master', commit='bgcdf3123',
            commit_date=datetime.datetime.now(),
            author='tião', title='something'
        )

        yield from self.revision.save()

        self.buildset = yield from build.BuildSet.create(
            repository=self.repo, revision=self.revision)

        yield from self.buildset.save()

        self.builder = build.Builder(repository=self.repo, name='builder-1')
        yield from self.builder.save()
        self.other_builder = build.Builder(repository=self.repo,
                                           name='builder-2')
        yield from self.other_builder.save()
        yield from self.builder.save()

        self.build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='v0.1',
                                 builder=self.builder)

        self.buildset.builds.append(self.build)
        yield from self.buildset.save()
