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
from datetime import datetime
from unittest.mock import Mock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.master import hole, build


class HoleHandlerTest(AsyncTestCase):

    def tearDown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(asyncio.gather(*asyncio.Task.all_tasks()))
        hole.Slave.drop_collection()
        hole.Repository.drop_collection()
        build.Builder.drop_collection()
        build.Build.drop_collection()
        super().tearDown()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(hole.Repository, 'first_run', Mock())
    @gen_test
    def test_repo_add(self):
        yield from self._create_test_data()

        data = {'url': 'git@somehere.com',
                'vcs_type': 'git',
                'update_seconds': 300,
                'slaves': [('127.0.0.1', 7777)]}
        action = 'repo-add'
        handler = hole.HoleHandler(data, action)
        repo = yield from handler.repo_add()

        self.assertTrue(repo['repo-add']['_id'])

    @gen_test
    def test_repo_remove(self):
        yield from self._create_test_data()
        data = {'url': 'git@somewhere.com'}
        action = 'repo-remove'
        handler = hole.HoleHandler(data, action)
        yield from handler.repo_remove()

        self.assertEqual((yield hole.Repository.objects.count()), 0)

    @gen_test
    def test_repo_list(self):
        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'repo-list')
        repo_list = (yield from handler.repo_list())['repo-list']

        self.assertEqual(len(repo_list), 1)

    @gen_test
    def test_repo_update(self):
        yield from self._create_test_data()

        data = {'url': 'git@somewhere.com',
                'update_seconds': 60}
        action = 'repo-update'
        handler = hole.HoleHandler(data, action)
        yield from handler.repo_update()
        repo = yield from hole.Repository.get(self.repo.url)

        self.assertEqual(repo.update_seconds, 60)

    @gen_test
    def test_repo_add_slave(self):
        yield from self._create_test_data()

        slave = yield from hole.Slave.create(host='127.0.0.1', port=1234)
        self.repo.add_slave(slave)

        data = {'url': 'git@somewhere.com',
                'host': '127.0.0.1',
                'port': 1234}
        action = 'repo-add-slave'

        handler = hole.HoleHandler(data, action)

        yield from handler.repo_add_slave()

        repo = yield from hole.Repository.get(self.repo.url)

        self.assertEqual(repo.slaves[0], slave)

    @gen_test
    def test_repo_remove_slave(self):
        yield from self._create_test_data()

        slave = yield from hole.Slave.create(host='127.0.0.1', port=1234)
        self.repo.add_slave(slave)

        data = {'url': 'git@somewhere.com',
                'host': '127.0.0.1',
                'port': 1234}
        action = 'repo-add-slave'

        handler = hole.HoleHandler(data, action)

        yield from handler.repo_add_slave()

        handler = hole.HoleHandler(data, 'repo-remove-slave')
        yield from handler.repo_remove_slave()

        repo = yield from hole.Repository.get(self.repo.url)

        self.assertEqual(len(repo.slaves), 0)

    @gen_test
    def test_slave_add(self):
        data = {'host': '127.0.0.1', 'port': 1234}
        handler = hole.HoleHandler(data, 'slave-add')
        slave = (yield from handler.slave_add())['slave-add']

        self.assertTrue(slave['_id'])

    @gen_test
    def test_slave_remove(self):
        yield from self._create_test_data()
        data = {'host': '127.0.0.1', 'port': 7777}
        handler = hole.HoleHandler(data, 'slave-remove')
        yield from handler.slave_remove()

        self.assertEqual((yield hole.Slave.objects.count()), 0)

    @gen_test
    def test_slave_list(self):
        yield from self._create_test_data()
        handler = hole.HoleHandler({}, 'slave-list')
        slaves = (yield from handler.slave_list())['slave-list']

        self.assertEqual(len(slaves), 1)

    @gen_test
    def test_builder_list(self):
        yield from self._create_test_data()

        handler = hole.HoleHandler({}, 'builder-list')

        builders = (yield from handler.builder_list())['builder-list']
        self.assertEqual(len(builders), 3)

    @gen_test
    def test_builder_show(self):
        yield from self._create_test_data()

        data = {'name': 'b0', 'repo-url': self.repo.url}
        action = 'builder-show'
        handler = hole.HoleHandler(data, action)
        builder = (yield from handler.builder_show())['builder-show']

        self.assertEqual(len(builder['builds']), 1)

    @asyncio.coroutine
    def _create_test_data(self):
        self.slave = hole.Slave(host='127.0.0.1', port=7777)
        yield self.slave.save()
        self.repo = yield from hole.Repository.create(
            'git@somewhere.com', 300, 'git')
        self.builds = []
        for i in range(3):
            builder = build.Builder(name='b{}'.format(i), repository=self.repo)
            yield builder.save()
            build_inst = hole.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='v0.{}'.format(i),
                                    started=datetime.now(),
                                    finished=datetime.now(),
                                    builder=builder, status='success')
            yield build_inst.save()
