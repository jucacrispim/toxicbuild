# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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
import json
from unittest import mock, TestCase
from toxicbuild.core.exchange import JsonAckMessage as Message
from toxicbuild.master import pollers, repository, users, utils, coordination
from toxicbuild.master.exceptions import CloneException
from toxicbuild.master.exchanges import connect_exchanges, disconnect_exchanges
from tests import async_test, AsyncMagicMock


class GitPollerTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        await connect_exchanges()

    @classmethod
    @mock.patch('aioamqp.protocol.logger', mock.Mock())
    @async_test
    async def tearDownClass(cls):
        channel = await pollers.revisions_added.connection.protocol.channel()
        await channel.queue_delete(
            'toxicmaster.revisions_added_queue')
        await disconnect_exchanges()
        # await coordination.ToxicZKClient._zk_client.close()

    @mock.patch.object(pollers, 'get_vcs', mock.MagicMock())
    @async_test
    async def setUp(self):
        super(GitPollerTest, self).setUp()
        self.owner = users.User(email='a@a.com', password='adsf')
        await self.owner.save()
        self.repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.org/project.git',
            owner=self.owner, schedule_poller=False)

        self.repo.schedule = mock.Mock()
        await self.repo.bootstrap()
        self.poller = pollers.Poller(
            self.repo, vcs_type='git', workdir='workdir')
        self.poller.vcs.try_set_remote = AsyncMagicMock()

    @async_test
    def tearDown(self):
        channel = yield from repository.\
            scheduler_action.connection.protocol.channel()
        yield from channel.queue_delete(
            repository.scheduler_action.queue_name)
        yield from channel.queue_delete(
            repository.update_code.queue_name)
        yield from repository.RepositoryRevision.drop_collection()
        yield from repository.Repository.drop_collection()
        yield from users.User.drop_collection()
        super(GitPollerTest, self).tearDown()

    @async_test
    async def test_notify_changes(self):
        rev = mock.MagicMock()
        rev.id = 'asdf'
        await self.poller.notify_change(*[rev])
        consumer = await pollers.revisions_added.consume()
        async with consumer:
            msg = await consumer.fetch_message()
            await msg.acknowledge()

        has_msg = bool(msg)

        self.assertTrue(has_msg)

    @mock.patch.object(pollers, 'revisions_added', AsyncMagicMock())
    @async_test
    async def test_process_changes(self):
        # now in the future, of course!
        now = datetime.datetime.now() + datetime.timedelta(100)
        branches = [
            repository.RepositoryBranch(name='master',
                                        notify_only_latest=True),
            repository.RepositoryBranch(name='dev',
                                        notify_only_latest=False)]
        self.repo.branches = branches
        await self.repo.save()
        await self._create_db_revisions()

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'zé', 'title': 'sometitle'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'tião', 'title': 'other'}],
                    'dev': [{'commit': 'sdfljfew', 'commit_date': now,
                             'author': 'mariazinha', 'title': 'bla'},
                            {'commit': 'sdlfjslfer3', 'commit_date': now,
                             'author': 'jc', 'title': 'Our lord John Cleese'}],
                    'other': []}

        self.poller.vcs.get_revisions = gr

        await self.poller.process_changes()

        self.assertTrue(pollers.revisions_added.publish.called)

    @mock.patch.object(pollers, 'revisions_added', AsyncMagicMock())
    @mock.patch.object(pollers, 'MatchKeysDict', mock.MagicMock())
    @async_test
    async def test_process_changes_with_branches(self):
        # now in the future, of course!
        now = datetime.datetime.now() + datetime.timedelta(100)
        branches = [
            repository.RepositoryBranch(name='master',
                                        notify_only_latest=True),
            repository.RepositoryBranch(name='dev',
                                        notify_only_latest=False)]
        self.repo.branches = branches
        await self.repo.save()
        await self._create_db_revisions()

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'zé', 'title': 'sometitle'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'tião', 'title': 'other'}],
                    'dev': [{'commit': 'sdfljfew', 'commit_date': now,
                             'author': 'mariazinha', 'title': 'bla'},
                            {'commit': 'sdlfjslfer3', 'commit_date': now,
                             'author': 'jc', 'title': 'Our lord John Cleese'}],
                    'other': []}

        self.poller.vcs.get_revisions = gr

        await self.poller.process_changes(repo_branches={'master': True})

        self.assertTrue(pollers.revisions_added.publish.called)
        self.assertFalse(pollers.MatchKeysDict.called)

    @mock.patch.object(pollers, 'revisions_added', AsyncMagicMock())
    @async_test
    async def test_process_changes_no_revisions(self):
        # now in the future, of course!
        branches = [
            repository.RepositoryBranch(name='master',
                                        notify_only_latest=True),
            repository.RepositoryBranch(name='dev',
                                        notify_only_latest=False)]
        self.repo.branches = branches
        await self.repo.save()
        await self._create_db_revisions()

        @asyncio.coroutine
        def gr(*a, **kw):
            return {}

        self.poller.vcs.get_revisions = gr

        await self.poller.process_changes()

        self.assertFalse(pollers.revisions_added.publish.called)

    @async_test
    async def test_external_poll(self):
        await self._create_db_revisions()
        external_url = 'http://some-url.com/bla.git'
        external_name = 'other-repo'
        external_branch = 'master'
        into = 'external:master'
        self.poller.vcs.import_external_branch = AsyncMagicMock(
            spec=self.poller.vcs.import_external_branch)
        self.poller.poll = AsyncMagicMock(spec=self.poller.poll)
        await self.poller.external_poll(external_url, external_name,
                                        external_branch, into)
        self.assertTrue(self.poller.vcs.import_external_branch.called)
        self.assertTrue(self.poller.poll.called)

    @async_test
    async def test_poll(self):
        await self._create_db_revisions()

        now = datetime.datetime.now()

        def workdir_exists():
            return False

        self.CLONE_CALLED = False

        @asyncio.coroutine
        def clone(url):
            self.CLONE_CALLED = True
            return True

        @asyncio.coroutine
        def has_changes():
            return True

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'eu', 'title': 'something'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'eu', 'title': 'otherthing'}]}

        self.poller.vcs.get_revisions = gr
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.vcs.clone = clone
        self.poller.vcs.get_remote = AsyncMagicMock(
            return_value=self.poller.repository.url)
        self.poller.vcs.has_changes = has_changes

        await self.poller.poll()

        self.assertTrue(self.CLONE_CALLED)

    @async_test
    async def test_poll_with_clone_exception(self):

        def workdir_exists():
            return False

        @asyncio.coroutine
        def clone(url):
            raise CloneException

        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.log = mock.Mock()
        self.poller.vcs.clone = clone

        with self.assertRaises(CloneException):
            await self.poller.poll()

    @async_test
    async def test_poll_without_clone(self):
        await self._create_db_revisions()

        now = datetime.datetime.now()

        def workdir_exists():
            return True

        self.CLONE_CALLED = False

        @asyncio.coroutine
        def clone(url):
            self.CLONE_CALLED = True
            return True

        @asyncio.coroutine
        def has_changes():
            return True

        @asyncio.coroutine
        def gr(*a, **kw):
            return {'master': [{'commit': '123sdf', 'commit_date': now,
                                'author': 'eu', 'title': 'something'},
                               {'commit': 'asdf213', 'commit_date': now,
                                'author': 'eu', 'title': 'bla'}]}

        self.poller.vcs.get_revisions = gr
        self.poller.vcs.workdir_exists = workdir_exists
        self.poller.vcs.clone = clone
        self.poller.vcs.has_changes = has_changes
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: None)

        await self.poller.poll()

        self.assertFalse(self.CLONE_CALLED)

    @mock.patch.object(pollers, 'LoggerMixin', mock.Mock())
    @async_test
    async def test_poll_with_exception_processing_changes(self):
        self.poller.vcs.workdir_exists = mock.Mock(return_value=True)
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.log = mock.Mock()
        self.poller.vcs.clone = AsyncMagicMock()
        self.poller.process_changes = AsyncMagicMock(side_effect=Exception)
        self.poller.vcs.get_remote = AsyncMagicMock(
            return_value=self.poller.repository.url)
        await self.poller.poll()
        log_level = self.poller.log.call_args[1]['level']
        self.assertEqual(log_level, 'error')

    @async_test
    async def test_poll_with_submodule(self):
        self.poller.process_changes = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.vcs.workdir_exists = lambda: True
        update_submodule = mock.MagicMock(
            spec=self.poller.vcs.update_submodule)
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: update_submodule(*a, **kw))

        self.poller.vcs.get_remote = AsyncMagicMock(
            return_value=self.poller.repository.url)
        await self.poller.poll()

        self.assertTrue(update_submodule.called)

    @async_test
    async def test_poll_setting_remote(self):
        self.poller.process_changes = asyncio.coroutine(
            lambda *a, **kw: None)
        self.poller.vcs.workdir_exists = lambda: True
        update_submodule = mock.MagicMock(
            spec=self.poller.vcs.update_submodule)
        self.poller.vcs.update_submodule = asyncio.coroutine(
            lambda *a, **kw: update_submodule(*a, **kw))

        self.poller.vcs.get_remote = AsyncMagicMock(
            return_value=self.poller.repository.url)
        self.poller.vcs.set_remote = AsyncMagicMock(
            spec=self.poller.vcs.set_remote)
        self.poller.repository.fetch_url = 'git@otherplace.net/bla.git'
        await self.poller.poll()
        self.assertTrue(self.poller.vcs.try_set_remote.called)

    @async_test
    async def test_poll_already_polling(self):
        self.poller.process_changes = mock.MagicMock()
        self.poller.vcs.workdir_exists = lambda: True
        self.poller.vcs.update_submodule = mock.MagicMock()
        self.poller._is_polling = True
        await self.poller.poll()

        self.assertFalse(self.poller.process_changes.called)

    async def _create_db_revisions(self):
        await self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()

        for r in range(2):
            rev = repository.RepositoryRevision(
                repository=rep, commit='123asdf', branch='master',
                commit_date=now, author='zé', title='algo')

            await rev.save()

            rev = repository.RepositoryRevision(
                repository=rep, commit='123asef', branch='other',
                commit_date=now, author='tião', title='outro')

            await rev.save()


class PollerServerTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        await connect_exchanges()

    @classmethod
    @mock.patch('aioamqp.protocol.logger', mock.Mock())
    @async_test
    async def tearDownClass(cls):
        channel = await pollers.update_code.connection.protocol.channel()
        await channel.queue_delete(
            'toxicmaster.update_code_queue')
        await channel.queue_delete(
            'toxicmaster.revisions_added_queue')
        await channel.queue_delete(
            'toxicmaster.scheduler_action_queue')
        await disconnect_exchanges()

    def setUp(self):
        self.server = pollers.PollerServer()

    @mock.patch.object(pollers.update_code, 'consume', AsyncMagicMock(
        spec=pollers.update_code.consume))
    @async_test
    async def test_run(self):
        handle = mock.Mock()
        msg = mock.Mock()
        msg.body = {'repo_id': 'someid'}
        msg.acknowledge = AsyncMagicMock()
        consumer = pollers.update_code.consume.return_value
        consumer.fetch_message.return_value = msg
        tasks = []

        class Srv(pollers.PollerServer):

            def _handler_counter(self, msg):
                t = asyncio.ensure_future(super()._handler_counter(msg))
                tasks.append(t)
                self.stop()
                return t

            def handle_update_request(self, msg):
                handle()
                return AsyncMagicMock()()

        server = Srv()
        await server.run()
        await asyncio.gather(*tasks)
        self.assertTrue(handle.called)

    @mock.patch.object(pollers.update_code, 'consume', AsyncMagicMock(
        spec=pollers.update_code.consume))
    @async_test
    async def test_run_timeout(self):
        handle = mock.Mock()
        msg = mock.Mock()
        msg.body = {'repo_id': 'someid'}
        msg.acknowledge = AsyncMagicMock()

        class Srv(pollers.PollerServer):

            def handle_update_request(self, msg):
                self.stop()
                handle()
                return AsyncMagicMock()()

        server = Srv()

        async def fm(cancel_on_timeout=True):
            server.stop()
            raise utils.ConsumerTimeout

        consumer = pollers.update_code.consume.return_value
        consumer.fetch_message = fm
        await server.run()
        self.assertFalse(handle.called)

    @mock.patch.object(utils.asyncio, 'sleep', AsyncMagicMock())
    @async_test
    async def test_shutdown(self):

        server = pollers.PollerServer()
        server._running_tasks = 1
        sleep_mock = mock.Mock()

        def sleep(t):
            sleep_mock()
            server._running_tasks -= 1
            return AsyncMagicMock()()

        utils.asyncio.sleep = sleep
        await server.shutdown()
        self.assertTrue(sleep_mock.called)

    @mock.patch.object(pollers.PollerServer, 'shutdown', AsyncMagicMock(
        spec=pollers.PollerServer.shutdown))
    def test_sync_shutdown(self):
        server = pollers.PollerServer()
        server.sync_shutdown()
        self.assertTrue(server.shutdown.called)

    @mock.patch.object(pollers.Poller, 'poll', AsyncMagicMock(
        return_value=True))
    @async_test
    async def test_handle_update_request(self):
        user = users.User(email='a@a.com')
        await user.save()
        repo = pollers.Repository(url='http://someurl.com/repo.git',
                                  owner=user, vcs_type='git',
                                  name='bla-repo')
        await repo.save()
        channel, envelope, properties = AsyncMagicMock(), mock.Mock(), {}
        repo_id = str(repo.id)
        body = json.dumps({'repo_id': repo_id, 'vcs_type': 'git'}).encode()

        async with await pollers.poll_status.consume(
                routing_key=repo_id) as consumer:
            message = Message(channel, body, envelope, properties)
            await self.server.handle_update_request(message)
            msg = await consumer.fetch_message()
            self.assertTrue(msg)

    @mock.patch.object(pollers.Poller, 'poll', AsyncMagicMock(
        side_effect=Exception))
    @mock.patch.object(pollers.PollerServer, 'log', mock.Mock())
    @async_test
    async def test_handle_update_request_exception(self):
        user = users.User(email='a@a.com')
        await user.save()
        repo = pollers.Repository(url='http://someurl.com/repo.git',
                                  owner=user, vcs_type='git',
                                  name='bla-repo')
        await repo.save()
        channel, envelope, properties = AsyncMagicMock(), mock.Mock(), {}
        repo_id = str(repo.id)
        body = json.dumps({'repo_id': repo_id, 'vcs_type': 'git'}).encode()

        async with await pollers.poll_status.consume(
                routing_key=repo_id) as consumer:

            message = Message(channel, body, envelope, properties)
            await self.server.handle_update_request(message)
            msg = await consumer.fetch_message()
            self.assertTrue(msg)

    @mock.patch.object(pollers.Poller, 'external_poll', AsyncMagicMock(
        return_value=True))
    @async_test
    async def test_handle_update_request_external(self):
        user = users.User(email='a@a.com')
        await user.save()
        repo = pollers.Repository(url='http://someurl.com/repo.git',
                                  owner=user, vcs_type='git',
                                  name='bla-repo')
        await repo.save()
        channel, envelope, properties = AsyncMagicMock(), mock.Mock(), {}
        repo_id = str(repo.id)
        body = json.dumps({'repo_id': repo_id, 'vcs_type': 'git',
                           'external': {'url': 'http://someurl.com/git.bla',
                                        'name': 'other-repo',
                                        'branch': 'master',
                                        'into': 'other-repo:master'}}).encode()

        async with await pollers.poll_status.consume(
                routing_key=repo_id) as consumer:
            message = Message(channel, body, envelope, properties)
            await self.server.handle_update_request(message)
            msg = await consumer.fetch_message()
            self.assertTrue(msg)
