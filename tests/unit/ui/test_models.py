# -*- coding: utf-8 -*-

import asyncio
from unittest.mock import MagicMock, patch
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.ui import models, client


class BaseModelTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models, 'get_hole_client', MagicMock(
        spec=models.get_hole_client))
    @gen_test
    def test_get_client(self):
        yield from models.BaseModel.get_client()
        self.assertTrue(models.get_hole_client.called)


@asyncio.coroutine
def get_client_mock(r2s_return_value=None):
    cl = client.UIHoleClient('localhost', 6666)

    @asyncio.coroutine
    def r2s(action, body):
        if r2s_return_value is None:
            return {'id': '23sfs34', 'vcs_type': 'git', 'name': 'my-repo',
                    'update_seconds': 300, 'slaves':
                    [{'name': 'bla', 'id': '123sd', 'host': 'localhost',
                      'port': 1234}]}
        else:
            return r2s_return_value

    cl.request2server = r2s
    cl._connected = True
    return cl


class RepositoryTest(AsyncTestCase):

    def setUp(self):
        super().setUp()
        self.repository = models.Repository(id='313lsjdf', vcs_type='git',
                                            update_seconds=300, slaves=[],
                                            name='my-repo')

        self.repository.get_client = get_client_mock

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @gen_test
    def test_add(self):
        repo = yield from models.Repository.add('some-repo',
                                                'git@somewhere.com', 'git')
        self.assertTrue(repo.id)

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @gen_test
    def test_get(self):

        repo = yield from models.Repository.get(name='some-repo')
        self.assertTrue(repo.id)

    @patch.object(models.Repository, 'get_client', get_client_mock)
    @gen_test
    def test_repo_slaves(self):
        repo = yield from models.Repository.get(name='some-repo')
        self.assertEqual(type(repo.slaves[0]), models.Slave)

    @patch.object(models.Repository, 'get_client', lambda:
                  get_client_mock([{'name': 'repo0'}, {'name': 'repo1'}]))
    @gen_test
    def test_list(self):

        repos = yield from models.Repository.list()
        self.assertEqual(len(repos), 2)

    @gen_test
    def test_delete(self):
        self.repository.get_client = lambda: (
            yield from get_client_mock('ok'))

        resp = yield from self.repository.delete()
        self.assertEqual(resp, 'ok')

    @gen_test
    def test_add_slave(self):
        self.repository.get_client = lambda: (
            yield from get_client_mock('add slave ok'))

        slave = models.Slave(name='localslave', host='localhost', port=7777)
        resp = yield from self.repository.add_slave(slave)

        self.assertEqual(resp, 'add slave ok')

    @gen_test
    def test_remove_slave(self):
        self.repository.get_client = lambda: (
            yield from get_client_mock('remove slave ok'))

        slave = models.Slave(name='localslave', host='localhost', port=7777)
        resp = yield from self.repository.remove_slave(slave)

        self.assertEqual(resp, 'remove slave ok')

    @gen_test
    def test_start_build(self):
        self.repository.get_client = lambda: (
            yield from get_client_mock('start build ok'))

        resp = yield from self.repository.start_build('master',
                                                      builder_name='b0',
                                                      named_tree='v0.1')

        self.assertEqual(resp, 'start build ok')


class SlaveTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @patch.object(models.Slave, 'get_client', lambda: (
        yield from get_client_mock({'host': 'localhost'})))
    @gen_test
    def test_add(self):

        slave = yield from models.Slave.add('localslave', 'localhost', 8888)
        self.assertEqual(slave.host, 'localhost')

    @patch.object(models.Slave, 'get_client', lambda: (
        yield from get_client_mock({'host': 'localhost', 'name': 'slave'})))
    @gen_test
    def test_get(self):

        slave = yield from models.Slave.get(name='slave')
        self.assertEqual(slave.name, 'slave')

    @patch.object(models.Slave, 'get_client', lambda: (
        yield from get_client_mock([{'name': 'slave0'}, {'name': 'slave1'}])))
    @gen_test
    def test_list(self):

        slaves = yield from models.Slave.list()
        self.assertEqual(len(slaves), 2)

    @gen_test
    def test_delete(self):
        slave = models.Slave(name='slave', host='localhost', port=1234)
        slave.get_client = lambda: (yield from get_client_mock('ok'))

        resp = yield from slave.delete()
        self.assertEqual(resp, 'ok')
