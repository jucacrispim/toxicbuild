# -*- coding: utf-8 -*-
# Copyright 2018, 2023 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import Mock, patch, AsyncMock
from toxicbuild.master import consumers
from tests import async_test


class BaseConsumerTest(TestCase):

    def setUp(self):

        handle = Mock()
        self.handle = handle
        self.msg = Mock()
        self.msg.body = {'repo_id': 'someid'}
        self.msg.acknowledge = AsyncMock()
        self.exchange = AsyncMock()
        self.consumer = self.exchange.consume.return_value
        self.consumer.fetch_message.return_value = self.msg

        class Srv(consumers.BaseConsumer):

            def handle_update_request(self, msg):
                self.stop()
                handle()
                return AsyncMock()()

        self.srv_class = Srv

    @async_test
    async def test_run(self):
        server = self.srv_class(self.exchange, lambda: None)
        server.msg_callback = server.handle_update_request
        await server.run()
        self.assertTrue(self.handle.called)

    @async_test
    async def test_run_routing_key(self):
        server = self.srv_class(self.exchange, lambda: None, routing_key='bla')
        server.msg_callback = server.handle_update_request
        await server.run()
        self.assertTrue(self.handle.called)
        kw = self.exchange.consume.call_args[1]
        self.assertIn('routing_key', kw.keys())
        self.assertIn('bla', kw.values())

    @async_test
    async def test_run_timeout(self):
        server = self.srv_class(self.exchange, AsyncMock())

        async def fm(cancel_on_timeout=True):
            server.stop()
            raise consumers.ConsumerTimeout

        consumer = self.exchange.consume.return_value.__aenter__.return_value
        consumer.fetch_message = fm
        await server.run()
        self.assertFalse(self.handle.called)

    @patch.object(consumers.LoggerMixin, 'log', Mock())
    @patch.object(consumers.BaseConsumer, 'reconnect_exchanges',
                  AsyncMock(
                      spec=consumers.BaseConsumer.reconnect_exchanges))
    @async_test
    async def test_run_connection_closed(self):
        server = self.srv_class(self.exchange, AsyncMock())

        async def fm(cancel_on_timeout=True):
            server.stop()
            raise consumers.AmqpClosedConnection

        consumer = self.exchange.consume.return_value.__aenter__.return_value
        consumer.fetch_message = fm
        await server.run()
        self.assertFalse(self.handle.called)
        self.assertTrue(consumers.BaseConsumer.reconnect_exchanges.called)

    @patch.object(consumers.asyncio, 'sleep', AsyncMock())
    @async_test
    async def test_shutdown(self):

        exchange = AsyncMock()
        server = consumers.BaseConsumer(exchange, lambda: None)
        server._running_tasks = 1
        sleep_mock = Mock()

        def sleep(t):
            sleep_mock()
            server._running_tasks -= 1
            return AsyncMock()()

        consumers.asyncio.sleep = sleep
        await server.shutdown()
        self.assertTrue(sleep_mock.called)

    @patch.object(consumers.BaseConsumer, 'shutdown', AsyncMock(
        spec=consumers.BaseConsumer.shutdown))
    def test_sync_shutdown(self):
        exchange = AsyncMock()
        server = consumers.BaseConsumer(exchange, lambda: None)
        server.sync_shutdown()
        self.assertTrue(server.shutdown.called)

    @patch.object(consumers.conn, 'reconnect', AsyncMock(
        spec=consumers.conn.reconnect))
    @async_test
    async def test_reconnect_exchanges(self):
        server = consumers.BaseConsumer(AsyncMock(), lambda: None)
        await server.reconnect_exchanges()

        self.assertTrue(consumers.conn.reconnect.called)


class RepositoryMessageConsumerTest(TestCase):

    def tearDown(self):
        consumers.RepositoryMessageConsumer._stop_consuming_messages = False

    @patch.object(consumers.Repository, 'get', AsyncMock())
    @patch.object(consumers.RepositoryRevision, 'objects', Mock())
    @async_test
    async def test_add_builds(self):
        repo = AsyncMock()
        repo.build_manager = AsyncMock()
        consumers.Repository.get.return_value = repo
        msg = AsyncMock()
        msg.body = {'repository_id': 'asdf',
                    'revisions_ids': []}
        to_list = AsyncMock()
        consumers.RepositoryRevision\
            .objects.filter.return_value.to_list = to_list
        message_consumer = consumers.RepositoryMessageConsumer()

        await message_consumer.add_builds(msg)
        self.assertTrue(consumers.Repository.get.called)
        self.assertTrue(to_list.called)

    @patch.object(consumers.Repository, 'get', AsyncMock())
    @patch.object(consumers.RepositoryRevision, 'objects', Mock())
    @patch.object(consumers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_add_builds_exception(self):
        repo = AsyncMock()
        consumers.Repository.get.return_value = repo
        msg = AsyncMock()
        msg.body = {'repository_id': 'asdf', 'revisions_ids': []}
        to_list = AsyncMock(side_effect=Exception)
        consumers.RepositoryRevision\
            .objects.filter.return_value.to_list = to_list
        message_consumer = consumers.RepositoryMessageConsumer()
        await message_consumer.add_builds(msg)
        self.assertTrue(consumers.Repository.get.called)
        self.assertTrue(to_list.called)

    @patch.object(consumers.Repository, 'get', AsyncMock(
        side_effect=consumers.Repository.DoesNotExist))
    @patch.object(consumers.LoggerMixin, 'log', Mock())
    @patch.object(consumers.RepositoryRevision, 'objects', Mock())
    @async_test
    async def test_add_builds_repo_dont_exist(self):
        msg = AsyncMock()
        msg.body = {'repository_id': 'asdf'}
        to_list = AsyncMock()
        consumers.RepositoryRevision\
            .objects.filter.return_value.to_list = to_list
        message_consumer = consumers.RepositoryMessageConsumer()
        await message_consumer.add_builds(msg)
        self.assertTrue(consumers.Repository.get.called)
        self.assertFalse(to_list.called)

    @patch.object(consumers.Repository, 'get', AsyncMock())
    @async_test
    async def test_add_requested_build(self):
        repo = AsyncMock()
        consumers.Repository.get.return_value = repo
        msg = AsyncMock()
        msg.body = {'repository_id': 'asdf',
                    'branch': 'master'}
        message_consumer = consumers.RepositoryMessageConsumer()
        await message_consumer.add_requested_build(msg)
        self.assertTrue(repo.start_build.called)

    @patch.object(consumers.Repository, 'get', AsyncMock(
        return_value=None))
    @async_test
    async def test_add_requested_build_no_repo(self):
        msg = AsyncMock()
        msg.body = {'repository_id': 'asdf',
                    'branch': 'master'}
        message_consumer = consumers.RepositoryMessageConsumer()
        await message_consumer.add_requested_build(msg)

    @patch.object(consumers.Repository, 'get', AsyncMock())
    @patch.object(consumers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_add_requested_build_exception(self):
        repo = AsyncMock()
        consumers.Repository.get.return_value = repo
        msg = AsyncMock()
        msg.body = {'repository_id': 'asdf'}
        message_consumer = consumers.RepositoryMessageConsumer()
        await message_consumer.add_requested_build(msg)
        self.assertFalse(repo.start_build.called)
        self.assertTrue(consumers.LoggerMixin.log.called)

    @patch.object(consumers.RepositoryMessageConsumer, '_get_repo_from_msg',
                  AsyncMock(return_value=None))
    @async_test
    async def test_remove_repo_no_repo(self):
        msg = AsyncMock()
        msg.body = {'repository_id': 'some-id'}
        message_consumer = consumers.RepositoryMessageConsumer()
        r = await message_consumer.remove_repo(msg)
        self.assertFalse(r)

    @patch.object(consumers.RepositoryMessageConsumer, '_get_repo_from_msg',
                  AsyncMock(spec=consumers.RepositoryMessageConsumer.
                            _get_repo_from_msg))
    @async_test
    async def test_remove_repo(self):
        msg = AsyncMock()
        msg.body = {'repository_id': 'some-id'}
        message_consumer = consumers.RepositoryMessageConsumer()
        r = await message_consumer.remove_repo(msg)
        repo = message_consumer._get_repo_from_msg.\
            return_value
        self.assertTrue(repo.remove.called)
        self.assertTrue(r)

    @patch.object(consumers.RepositoryMessageConsumer, '_get_repo_from_msg',
                  AsyncMock(spec=consumers.RepositoryMessageConsumer.
                            _get_repo_from_msg))
    @patch.object(consumers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_remove_repo_exception(self):
        repo = consumers.RepositoryMessageConsumer._get_repo_from_msg.\
            return_value
        repo.remove.side_effect = Exception
        msg = AsyncMock()
        msg.body = {'repository_id': 'some-id'}
        message_consumer = consumers.RepositoryMessageConsumer()
        r = await message_consumer.remove_repo(msg)
        self.assertTrue(repo.remove.called)
        self.assertTrue(consumers.LoggerMixin.log.called)
        self.assertTrue(r)

    @patch.object(consumers.RepositoryMessageConsumer, '_get_repo_from_msg',
                  AsyncMock(spec=consumers.RepositoryMessageConsumer.
                            _get_repo_from_msg))
    @patch.object(consumers.Repository, 'update_code', AsyncMock(
        spec=consumers.Repository.update_code))
    @async_test
    async def test_update_repo(self):
        repo = consumers.RepositoryMessageConsumer.\
            _get_repo_from_msg.return_value
        msg = AsyncMock()
        msg.body = {'repository_id': 'some-id'}
        message_consumer = consumers.RepositoryMessageConsumer()
        r = await message_consumer.update_repo(msg)
        self.assertTrue(r)
        self.assertTrue(repo.update_code.called)

    @patch.object(consumers.RepositoryMessageConsumer, '_get_repo_from_msg',
                  AsyncMock(spec=consumers.RepositoryMessageConsumer.
                            _get_repo_from_msg))
    @patch.object(consumers.Repository, 'update_code', AsyncMock(
        spec=consumers.Repository.update_code))
    @patch.object(consumers.LoggerMixin, 'log', Mock())
    @async_test
    async def test_update_repo_exception(self):
        repo = consumers.RepositoryMessageConsumer._get_repo_from_msg.\
            return_value
        repo.update_code.side_effect = Exception
        msg = AsyncMock()
        msg.body = {'repository_id': 'some-id'}
        message_consumer = consumers.RepositoryMessageConsumer()
        r = await message_consumer.update_repo(msg)
        self.assertTrue(r)
        self.assertTrue(repo.update_code.called)
        self.assertTrue(consumers.LoggerMixin.log.called)

    @patch.object(consumers.RepositoryMessageConsumer, '_get_repo_from_msg',
                  AsyncMock(spec=consumers.RepositoryMessageConsumer.
                            _get_repo_from_msg,
                            return_value=None))
    @patch.object(consumers.Repository, 'update_code', AsyncMock(
        spec=consumers.Repository.update_code))
    @async_test
    async def test_update_repo_no_repo(self):
        msg = AsyncMock()
        msg.body = {'repository_id': 'some-id'}
        message_consumer = consumers.RepositoryMessageConsumer()
        r = await message_consumer.update_repo(msg)
        self.assertFalse(r)

    @patch.object(consumers.BaseConsumer, 'run', AsyncMock())
    def test_run(self):
        message_consumer = consumers.RepositoryMessageConsumer()

        message_consumer.run()
        self.assertTrue(all([message_consumer.revision_consumer.run.called,
                             message_consumer.build_consumer.run.called,
                             message_consumer.removal_consumer.run.called,
                             message_consumer.update_consumer.run.called]))
