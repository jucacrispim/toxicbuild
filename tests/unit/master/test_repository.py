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
from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from toxicbuild.core import utils, exchange
from toxicbuild.master import (repository, build, slave, users)
from toxicbuild.master.exchanges import (connect_exchanges,
                                         disconnect_exchanges)
from tests import async_test, AsyncMagicMock, create_autospec


class RepoPlugin(repository.MasterPlugin):
    name = 'repo-plugin'
    type = 'test'
    events = ['repo-event']

    @asyncio.coroutine
    def run(self, sender):
        pass


class RepositoryTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        await connect_exchanges()
        cls.exchange = None

    @classmethod
    @patch('aioamqp.protocol.logger', Mock())
    @async_test
    async def tearDownClass(cls):
        if cls.exchange:
            await cls.exchange.channel.queue_delete(
                'toxicmaster.poll_status_queue')
            await cls.exchange.channel.exchange_delete(
                'toxicmaster.poll_status')
            await cls.exchange.channel.queue_delete(
                'toxicmaster-repo-update-code-mutex-queue')
            await cls.exchange.channel.exchange_delete(
                'toxicmaster-repo-update-code-mutex')

        await disconnect_exchanges()

    @async_test
    async def setUp(self):
        super(RepositoryTest, self).setUp()
        await self._create_db_revisions()
        repository.Repository._running_builds = 0
        repository.Repository._stop_consuming_messages = False

    @async_test
    async def tearDown(self):
        await self.repo._delete_locks()
        await repository.Repository.drop_collection()
        await repository.RepositoryRevision.drop_collection()
        await repository.BuildSet.drop_collection()
        await slave.Slave.drop_collection()
        await build.Builder.drop_collection()
        repository.Repository._plugins_instances = {}
        await users.User.drop_collection()
        super(RepositoryTest, self).tearDown()

    @patch.object(repository.Repository, 'get', AsyncMagicMock())
    @patch.object(repository.RepositoryRevision, 'objects', Mock())
    @async_test
    async def test_add_builds_fn(self):
        repo = create_autospec(spec=repository.Repository,
                               mock_cls=AsyncMagicMock)
        repo.build_manager = AsyncMagicMock()
        repository.Repository.get.return_value = repo
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf',
                    'revisions_ids': []}
        to_list = AsyncMagicMock()
        repository.RepositoryRevision\
                  .objects.filter.return_value.to_list = to_list
        await repository.Repository._add_builds(msg)
        self.assertTrue(repository.Repository.get.called)
        self.assertTrue(to_list.called)
        self.assertTrue(msg.acknowledge.called)

    @patch.object(repository.Repository, 'get', AsyncMagicMock())
    @patch.object(repository.RepositoryRevision, 'objects', Mock())
    @patch.object(repository.utils, 'log', Mock())
    @async_test
    async def test_add_builds_fn_exception(self):
        repo = create_autospec(spec=repository.Repository,
                               mock_cls=AsyncMagicMock)
        repository.Repository.get.return_value = repo
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf', 'revisions_ids': []}
        to_list = AsyncMagicMock(side_effect=Exception)
        repository.RepositoryRevision\
                  .objects.filter.return_value.to_list = to_list
        await repository.Repository._add_builds(msg)
        self.assertTrue(repository.Repository.get.called)
        self.assertTrue(to_list.called)
        self.assertTrue(msg.acknowledge.called)

    @patch.object(repository.Repository, 'get', AsyncMagicMock(
        side_effect=repository.Repository.DoesNotExist))
    @patch.object(repository.RepositoryRevision, 'objects', Mock())
    @patch.object(repository.utils, 'log', Mock())
    @async_test
    async def test_add_builds_fn_repo_dont_exist(self):
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf'}
        to_list = AsyncMagicMock()
        repository.RepositoryRevision\
                  .objects.filter.return_value.to_list = to_list
        await repository.Repository._add_builds(msg)
        self.assertTrue(repository.Repository.get.called)
        self.assertFalse(to_list.called)
        self.assertTrue(msg.acknowledge.called)

    @patch.object(repository.Repository, 'get', AsyncMagicMock())
    @patch.object(repository.Slave, 'objects', Mock())
    @async_test
    async def test_add_requested_build(self):
        repo = create_autospec(spec=repository.Repository,
                               mock_cls=AsyncMagicMock)
        repository.Repository.get.return_value = repo
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf',
                    'branch': 'master',
                    'slaves_ids': [str(self.slave.id)]}
        to_list = AsyncMagicMock()
        repository.Slave.objects.filter.return_value.to_list = to_list
        await repository.Repository._add_requested_build(msg)
        self.assertTrue(repo.start_build.called)

    @patch.object(repository.Repository, 'get', AsyncMagicMock(
        return_value=None))
    @patch.object(repository.Slave, 'objects', Mock())
    @async_test
    async def test_add_requested_build_no_repo(self):
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf',
                    'branch': 'master',
                    'slave_ids': [str(self.slave.id)]}
        await repository.Repository._add_requested_build(msg)
        self.assertFalse(repository.Slave.objects.filter.called)

    @patch.object(repository.Repository, 'get', AsyncMagicMock())
    @patch.object(repository.Slave, 'objects', Mock())
    @async_test
    async def test_add_requested_build_no_slaves(self):
        repo = create_autospec(spec=repository.Repository,
                               mock_cls=AsyncMagicMock)
        repository.Repository.get.return_value = repo
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf',
                    'branch': 'master'}
        await repository.Repository._add_requested_build(msg)
        self.assertTrue(repo.start_build.called)

    @patch.object(repository.Repository, 'get', AsyncMagicMock())
    @patch.object(repository.utils, 'log', Mock())
    @async_test
    async def test_add_requested_build_exception(self):
        repo = create_autospec(spec=repository.Repository,
                               mock_cls=AsyncMagicMock)
        repository.Repository.get.return_value = repo
        msg = AsyncMagicMock()
        msg.body = {'repository_id': 'asdf'}
        await repository.Repository._add_requested_build(msg)
        self.assertFalse(repo.start_build.called)
        self.assertTrue(repository.utils.log.called)

    @patch.object(repository.Repository, '_add_builds', AsyncMagicMock())
    @patch.object(repository.revisions_added, 'consume', AsyncMagicMock())
    @async_test
    async def test_wait_revisions(self):

        consumer = repository.revisions_added.consume.return_value

        async def fm(cancel_on_timeout=False):
            repository.Repository._stop_consuming_messages = True

        consumer.fetch_message = fm
        await repository.Repository.wait_revisions()
        self.assertTrue(repository.Repository._add_builds.called)

    @patch.object(repository.Repository, '_add_builds', AsyncMagicMock())
    @patch.object(repository.revisions_added, 'consume', AsyncMagicMock())
    @async_test
    async def test_wait_revisions_timeout(self):

        consumer = repository.revisions_added.consume.return_value

        async def fm(cancel_on_timeout=False):
            repository.Repository._stop_consuming_messages = True
            raise repository.ConsumerTimeout

        consumer.fetch_message = fm
        await repository.Repository.wait_revisions()
        self.assertFalse(repository.Repository._add_builds.called)

    @patch.object(repository.repo_notifications, 'consume',
                  AsyncMagicMock(spec=repository.repo_notifications.consume))
    @patch.object(repository.Repository, '_add_requested_build',
                  AsyncMagicMock(
                      spec=repository.Repository._add_requested_build))
    @async_test
    async def test_wait_build_requests(self):
        consumer = repository.repo_notifications.consume.return_value

        async def fm(cancel_on_timeout=False):
            repository.Repository._stop_consuming_messages = True

        consumer.fetch_message = fm
        await repository.Repository.wait_build_requests()
        self.assertTrue(repository.Repository._add_requested_build.called)

    @patch.object(repository.repo_notifications, 'consume',
                  AsyncMagicMock(spec=repository.repo_notifications.consume))
    @patch.object(repository.Repository, '_add_requested_build',
                  AsyncMagicMock(
                      spec=repository.Repository._add_requested_build))
    @async_test
    async def test_wait_build_requests_timeout(self):
        consumer = repository.repo_notifications.consume.return_value

        async def fm(cancel_on_timeout=False):
            repository.Repository._stop_consuming_messages = True
            raise repository.ConsumerTimeout

        consumer.fetch_message = fm
        await repository.Repository.wait_build_requests()
        self.assertFalse(repository.Repository._add_requested_build.called)

    @patch.object(repository.Repository, '_get_repo_from_msg', AsyncMagicMock(
        spec=repository.Repository._get_repo_from_msg, return_value=None))
    @async_test
    async def test_remove_repo_no_repo(self):
        r = await repository.Repository._remove_repo({})
        self.assertFalse(r)

    @patch.object(repository.Repository, '_get_repo_from_msg', AsyncMagicMock(
        spec=repository.Repository._get_repo_from_msg,
        return_value=create_autospec(spec=repository.Repository,
                                     mock_cls=AsyncMagicMock)))
    @async_test
    async def test_remove_repo(self):
        r = await repository.Repository._remove_repo({})
        repo = repository.Repository._get_repo_from_msg.return_value
        self.assertTrue(repo.remove.called)
        self.assertTrue(r)

    @patch.object(repository.Repository, '_get_repo_from_msg', AsyncMagicMock(
        spec=repository.Repository._get_repo_from_msg,
        return_value=create_autospec(spec=repository.Repository,
                                     mock_cls=AsyncMagicMock)))
    @patch.object(repository.utils, 'log', Mock())
    @async_test
    async def test_remove_repo_exception(self):
        repo = repository.Repository._get_repo_from_msg.return_value
        repo.remove.side_effect = Exception
        r = await repository.Repository._remove_repo({})
        self.assertTrue(repo.remove.called)
        self.assertTrue(repository.utils.log.called)
        self.assertTrue(r)

    @patch.object(repository.repo_notifications, 'consume',
                  AsyncMagicMock(spec=repository.repo_notifications.consume))
    @patch.object(repository.Repository, '_remove_repo',
                  AsyncMagicMock(spec=repository.Repository._remove_repo))
    @async_test
    async def test_wait_removal_request(self):
        consumer = repository.repo_notifications.consume.return_value

        async def fm(cancel_on_timeout=False):
            repository.Repository._stop_consuming_messages = True

        consumer.fetch_message = fm
        await repository.Repository.wait_removal_request()
        kw = repository.repo_notifications.consume.call_args[1]
        self.assertTrue(repository.Repository._remove_repo.called)
        self.assertEqual(kw['routing_key'], 'repo-removal-requested')

    @patch.object(repository.repo_notifications, 'consume',
                  AsyncMagicMock(spec=repository.repo_notifications.consume))
    @patch.object(repository.Repository, '_remove_repo',
                  AsyncMagicMock(spec=repository.Repository._remove_repo))
    @async_test
    async def test_wait_removal_request_timeout(self):
        consumer = repository.repo_notifications.consume.return_value

        async def fm(cancel_on_timeout=False):
            repository.Repository.stop_consuming_messages()
            raise repository.ConsumerTimeout

        consumer.fetch_message = fm
        await repository.Repository.wait_removal_request()
        self.assertFalse(repository.Repository._remove_repo.called)

    @async_test
    async def test_to_dict(self):
        d = await self.repo.to_dict()
        self.assertTrue(d['id'])
        self.assertTrue('plugins' in d.keys())

    @async_test
    async def test_to_dict_id_as_str(self):
        d = await self.repo.to_dict(True)
        self.assertIsInstance(d['id'], str)

    @patch.object(repository, 'repo_notifications', AsyncMagicMock(
        spec=repository.repo_notifications))
    @async_test
    async def test_request_removal(self):
        await self.repo.request_removal()
        self.assertTrue(repository.repo_notifications.publish.called)

    # @patch.object(repository.Repository, 'objects', AsyncMagicMock())
    # @async_test
    # async def test_get_repo(self):
    #     repo = await repository.Repository.get(id='some-id')
    #     self.assertTrue(repository.Repository.objects.get.called)
    #     self.assertTrue(repo._create_locks.called)

    def test_vcs(self):
        self.assertTrue(self.repo.vcs)

    def test_workdir(self):
        expected = 'src/git-somewhere.com-project.git/{}'.format(str(
            self.repo.id))
        self.assertEqual(self.repo.workdir, expected)

    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_create(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123',
                                              owner=self.owner)
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst])

        self.assertTrue(repo.id)
        self.assertTrue(repository.repo_added.publish.called)
        slaves = await repo.slaves
        self.assertEqual(slaves[0], slave_inst)

    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_create_with_branches(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123;_',
                                              owner=self.owner)
        branches = [repository.RepositoryBranch(name='branch{}'.format(str(i)),
                                                notify_only_latest=bool(i))
                    for i in range(3)]

        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst],
            branches=branches)

        self.assertTrue(repo.id)
        self.assertEqual(len(repo.branches), 3)

    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(repository, 'shutil', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_remove(self):
        repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git')

        repo.schedule()
        builder = repository.Builder(name='b1', repository=repo)
        await builder.save()
        await repo._create_locks()
        await repo.remove()

        builders_count = await repository.Builder.objects.filter(
            repository=repo).count()

        self.assertEqual(builders_count, 0)

        with self.assertRaises(repository.Repository.DoesNotExist):
            await repository.Repository.get(url=repo.url)

        self.assertIsNone(repository._scheduler_hashes.get(repo.url))
        self.assertIsNone(repository._scheduler_hashes.get(
            '{}-start-pending'.format(repo.url)))
        self.assertTrue(repository.scheduler_action.publish.called)

    @patch.object(repository, 'repo_added', AsyncMagicMock())
    @patch.object(repository.Repository, '_create_locks', AsyncMagicMock())
    @patch.object(repository.Repository, 'log', Mock())
    @async_test
    async def test_get(self):
        slave_inst = await slave.Slave.create(name='name', host='bla.com',
                                              port=1234, token='123',
                                              owner=self.owner)
        old_repo = await repository.Repository.create(
            name='reponame', url='git@somewhere.com', owner=self.owner,
            update_seconds=300, vcs_type='git', slaves=[slave_inst])

        new_repo = await repository.Repository.get(url=old_repo.url)

        slaves = await new_repo.slaves
        self.assertEqual(old_repo, new_repo)
        self.assertEqual(slaves[0], slave_inst)

    @patch.object(repository, 'update_code', AsyncMagicMock())
    @patch.object(repository, 'repo_status_changed', AsyncMagicMock())
    @patch.object(exchange, 'uuid4', MagicMock())
    @async_test
    async def test_update_code_with_clone_exception(self, *args, **kwargs):
        uuid4_ret = uuid4()
        exchange.uuid4.return_value = uuid4_ret
        queue_name = '{}-consumer-queue-{}'.format(repository.poll_status.name,
                                                   str(uuid4_ret))
        await repository.poll_status.bind(routing_key=str(self.repo.id),
                                          queue_name=queue_name)
        await repository.poll_status.publish(
            {'with_clone': True,
             'clone_status': 'clone-exception'},
            routing_key=str(self.repo.id))
        await self.repo.save()
        # await self.repo._create_locks()
        await self.repo.update_code()
        # await self.repo._delete_locks()
        await self.repo.reload()
        self.assertEqual(self.repo.clone_status, 'clone-exception')

    @async_test
    async def test_delete_locks_timeout(self):
        await self.repo.save()
        self.repo.log = Mock()
        self.repo.toxicbuild_conf_lock = AsyncMagicMock()
        self.repo.update_code_lock = AsyncMagicMock()
        self.repo.toxicbuild_conf_lock.consume.\
            side_effect = repository.ConsumerTimeout

        await self.repo._delete_locks()
        self.assertTrue(self.repo.log.called)

    @patch.object(repository, 'update_code', AsyncMagicMock())
    @patch.object(exchange, 'uuid4', MagicMock())
    @async_test
    async def test_update_code(self):
        self.repo.clone_status = 'cloning'
        uuid4_ret = exchange.uuid4()
        exchange.uuid4.return_value = uuid4_ret
        queue_name = '{}-consumer-queue-{}'.format(repository.poll_status.name,
                                                   str(uuid4_ret))
        await repository.poll_status.bind(routing_key=str(self.repo.id),
                                          queue_name=queue_name)

        await repository.poll_status.publish(
            {'with_clone': False,
             'clone_status': 'ready'},
            routing_key=str(self.repo.id))
        await self.repo.save()
        # await self.repo._create_locks()
        await self.repo.update_code()
        # await self.repo._delete_locks()
        await asyncio.sleep(0.1)
        await self.repo.reload()
        self.assertEqual(self.repo.clone_status, 'ready')

    @patch.object(repository, 'update_code', AsyncMagicMock())
    @patch.object(exchange, 'uuid4', MagicMock())
    @async_test
    async def test_update_code_waiting_lock(self):
        self.repo.clone_status = 'cloning'
        uuid4_ret = exchange.uuid4()
        exchange.uuid4.return_value = uuid4_ret
        queue_name = '{}-consumer-queue-{}'.format(repository.poll_status.name,
                                                   str(uuid4_ret))
        await repository.poll_status.bind(routing_key=str(self.repo.id),
                                          queue_name=queue_name)

        await repository.poll_status.publish(
            {'with_clone': False,
             'clone_status': 'ready'},
            routing_key=str(self.repo.id))
        await self.repo.save()
        # await self.repo._create_locks()
        await self.repo.update_code(wait_for_lock=True)
        # await self.repo._delete_locks()
        await asyncio.sleep(0.1)
        await self.repo.reload()
        self.assertEqual(self.repo.clone_status, 'ready')

    @patch.object(exchange, 'uuid4', MagicMock())
    @async_test
    async def test_update_code_locked(self):
        self.repo.clone_status = 'cloning'
        await self.repo.save()
        lock = await self.repo.update_code_lock.try_acquire(
            routing_key=str(self.repo.id))
        async with lock:
            self.repo.get_url = MagicMock(spec=self.repo.get_url)
            await self.repo.update_code()
            self.assertFalse(self.repo.get_url.called)

    @patch.object(exchange, 'uuid4', MagicMock())
    @patch.object(repository, 'update_code', AsyncMagicMock())
    @patch.object(repository, 'repo_status_changed', AsyncMagicMock())
    @async_test
    async def test_update_with_clone_sending_signal(self):
        self.repo.clone_status = 'cloning'
        await self.repo.save()
        self.repo._poller_instance = MagicMock()
        uuid4_ret = exchange.uuid4()
        exchange.uuid4.return_value = uuid4_ret
        queue_name = '{}-consumer-queue-{}'.format(repository.poll_status.name,
                                                   str(uuid4_ret))
        await repository.poll_status.bind(routing_key=str(self.repo.id),
                                          queue_name=queue_name)

        await repository.poll_status.publish(
            {'with_clone': True,
             'clone_status': 'ready'},
            routing_key=str(self.repo.id))

        self.repo._poller_instance.poll = asyncio.coroutine(lambda: True)
        # await self.repo._create_locks()
        await self.repo.update_code()
        # await self.repo._delete_locks()
        self.assertTrue(repository.repo_status_changed.publish.called)

    @async_test
    async def test_bootstrap(self):
        self.repo.schedule = Mock()
        await self.repo.bootstrap()
        self.assertTrue(self.repo.schedule.called)

    @patch.object(repository.Repository, 'bootstrap', AsyncMagicMock())
    @async_test
    async def test_bootstrap_all(self):
        await repository.Repository.bootstrap_all()
        self.assertTrue(repository.Repository.bootstrap.called)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    def test_schedule(self):
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        plugin = MagicMock
        plugin.name = 'my-plugin'
        plugin.run = AsyncMagicMock()
        self.repo.plugins = [plugin]
        self.repo.schedule()

        self.assertTrue(self.repo.scheduler.add.called)
        self.assertTrue(self.repo.plugins[0].called)
        self.assertTrue(repository.scheduler_action.publish.called)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    def test_schedule_no_poller(self):
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        plugin = MagicMock
        plugin.name = 'my-plugin'
        plugin.run = AsyncMagicMock()
        self.repo.plugins = [plugin]
        self.repo.schedule_poller = False
        self.repo.schedule()

        self.assertTrue(self.repo.scheduler.add.called)
        self.assertTrue(self.repo.plugins[0].called)
        self.assertFalse(repository.scheduler_action.publish.called)

    @patch.object(repository.utils, 'log', Mock())
    @patch.object(repository.scheduler_action, 'publish', AsyncMagicMock())
    @patch('toxicbuild.master.scheduler')
    @async_test
    async def test_schedule_all(self, *a, **kw):
        # await self._create_db_revisions()
        self.repo.scheduler = Mock(spec=self.repo.scheduler)
        await self.repo.schedule_all()
        from toxicbuild.master import scheduler
        self.assertTrue(scheduler.add.called)

    @async_test
    async def test_add_slave(self):
        # await self._create_db_revisions()
        slave = await repository.Slave.create(name='name',
                                              host='127.0.0.1',
                                              port=7777,
                                              token='123',
                                              owner=self.owner)

        await self.repo.add_slave(slave)
        slaves = await self.repo.slaves
        self.assertEqual(len(slaves), 2)

    @async_test
    async def test_remove_slave(self):
        # await self._create_db_revisions()
        slave = await repository.Slave.create(name='name',
                                              host='127.0.0.1',
                                              port=7777,
                                              token='123',
                                              owner=self.owner)
        await self.repo.add_slave(slave)
        await self.repo.remove_slave(slave)

        self.assertEqual(len((await self.repo.slaves)), 1)

    @async_test
    async def test_add_branch(self):
        # await self._create_db_revisions()
        await self.repo.add_or_update_branch('master')
        self.assertEqual(len(self.repo.branches), 1)

    @patch.object(repository.Repository, '_create_locks', AsyncMagicMock())
    @async_test
    async def test_update_branch(self):
        await self.repo.add_or_update_branch('master')
        await self.repo.add_or_update_branch('other-branch')
        await self.repo.add_or_update_branch('master', True)
        repo = await repository.Repository.get(id=self.repo.id)
        self.assertTrue(repo.branches[0].notify_only_latest)
        self.assertEqual(len(repo.branches), 2)

    @async_test
    async def test_remove_branch(self):
        await self.repo.add_or_update_branch('master')
        await self.repo.remove_branch('master')
        self.assertTrue(len(self.repo.branches), 0)

    @async_test
    async def test_get_latest_revision_for_branch(self):
        # await self._create_db_revisions()
        expected = '123asdf1'
        rev = await self.repo.get_latest_revision_for_branch('master')
        self.assertEqual(expected, rev.commit)

    @async_test
    async def test_get_latest_revision_for_branch_without_revision(self):
        rev = await self.repo.get_latest_revision_for_branch('nonexistant')
        self.assertIsNone(rev)

    @async_test
    async def test_get_latest_revisions(self):
        revs = await self.repo.get_latest_revisions()

        self.assertEqual(revs['master'].commit, '123asdf1')
        self.assertEqual(revs['dev'].commit, '123asdf1')

    @async_test
    async def test_get_known_branches(self):
        expected = ['master', 'dev']
        returned = await self.repo.get_known_branches()

        self.assertTrue(expected, returned)

    @async_test
    async def test_add_revision(self):
        await self.repo.save()
        branch = 'master'
        commit = 'asdf213'
        commit_date = datetime.datetime.now()
        kw = {'commit': commit, 'commit_date': commit_date,
              'author': 'someone', 'title': 'uhuuu!!'}
        rev = await self.repo.add_revision(branch, **kw)
        self.assertTrue(rev.id)
        self.assertEqual('uhuuu!!', rev.title)

    @async_test
    async def test_add_revision_external(self):
        await self.repo.save()
        branch = 'master'
        commit = 'asdf213'
        commit_date = datetime.datetime.now()
        kw = {'commit': commit, 'commit_date': commit_date,
              'author': 'someone', 'title': 'uhuuu!!'}
        external = {'url': 'http://bla.com/bla.git', 'name': 'remote',
                    'branch': 'master', 'into': 'bla'}
        rev = await self.repo.add_revision(branch, external=external, **kw)
        self.assertTrue(rev.id)
        self.assertEqual('uhuuu!!', rev.title)
        self.assertTrue(rev.external)

    @async_test
    async def test_enable_plugin(self):
        await self.repo.save()
        await self.repo.enable_plugin('repo-plugin')
        self.assertEqual(len(self.repo.plugins), 1)

    @async_test
    async def test_get_plugins_for_event(self):
        await self.repo.save()
        await self.repo.enable_plugin('repo-plugin')
        plugins = self.repo.get_plugins_for_event('repo-event')
        self.assertEqual(len(plugins), 1)

    def test_match_kw(self):
        plugin = repository.MasterPlugin()
        kw = {'name': 'BaseMasterPlugin', 'type': None}
        match = self.repo._match_kw(plugin, **kw)
        self.assertTrue(match)

    def test_match_not_matching(self):
        plugin = repository.MasterPlugin()
        kw = {'name': 'BaseMasterPlugin', 'type': 'bla'}
        match = self.repo._match_kw(plugin, **kw)
        self.assertFalse(match)

    def test_test_match_bad_attr(self):
        plugin = repository.MasterPlugin()
        kw = {'name': 'BaseMasterPlugin', 'other': 'ble'}
        match = self.repo._match_kw(plugin, **kw)
        self.assertFalse(match)

    @async_test
    async def test_disable_plugin(self):
        await self.repo.save()
        await self.repo.enable_plugin('repo-plugin')
        kw = {'name': 'repo-plugin'}
        await self.repo.disable_plugin(**kw)
        self.assertEqual(len(self.repo.plugins), 0)

    @async_test
    async def test_add_builds_for_slave(self):
        await self.repo.save()
        add_builds_for_slave = MagicMock(
            spec=build.BuildManager.add_builds_for_slave)
        self.repo.build_manager.add_builds_for_slave = asyncio.coroutine(
            lambda *a, **kw: add_builds_for_slave(*a, **kw))

        buildset = MagicMock()
        slave = MagicMock()
        builders = [MagicMock()]
        args = (buildset, slave)

        await self.repo.add_builds_for_slave(*args, builders=builders)

        called_args = add_builds_for_slave.call_args[0]

        self.assertEqual(called_args, args)
        called_kw = add_builds_for_slave.call_args[1]
        self.assertEqual(called_kw['builders'], builders)

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_with_running_build(self):

        running_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='running', builder=self.builder)
        buildset = await build.BuildSet.create(repository=self.repo,
                                               revision=self.revs[0])

        buildset.builds.append(running_build)
        await buildset.save()
        self.assertEqual((await self.repo.get_status()), 'running')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_with_success_build(self):

        success_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='master',
                                    started=datetime.datetime.now(),
                                    status='success', builder=self.builder)

        pending_build = build.Build(repository=self.repo, slave=self.slave,
                                    branch='master', named_tree='v0.1',
                                    builder=self.builder)
        builds = [success_build, pending_build]
        for i, b in enumerate(builds):
            buildset = await build.BuildSet.create(repository=self.repo,
                                                   revision=self.revs[i])
            buildset.builds.append(b)
            await buildset.save()

        self.assertEqual((await self.repo.get_status()), 'success')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_with_fail_build(self):

        fail_build = build.Build(repository=self.repo, slave=self.slave,
                                 branch='master', named_tree='master',
                                 started=datetime.datetime.now(),
                                 status='fail', builder=self.builder)
        buildset = await build.BuildSet.create(repository=self.repo,
                                               revision=self.revs[0])

        buildset.builds.append(fail_build)
        await buildset.save()
        self.assertEqual((await self.repo.get_status()), 'fail')

    @async_test
    async def test_get_status_cloning_repo(self):
        self.repo.clone_status = 'cloning'
        status = await self.repo.get_status()
        self.assertEqual(status, 'cloning')

    @async_test
    async def test_get_status_clone_exception(self):
        self.repo.clone_status = 'clone-exception'
        status = await self.repo.get_status()
        self.assertEqual(status, 'clone-exception')

    @async_test
    async def test_get_status_without_build(self):

        self.assertEqual((await self.repo.get_status()), 'ready')

    @patch.object(build.BuildSet, 'notify', AsyncMagicMock(
        spec=build.BuildSet.notify))
    @async_test
    async def test_get_status_only_pending(self):

        p_build = build.Build(repository=self.repo, slave=self.slave,
                              branch='master', named_tree='master',
                              started=datetime.datetime.now(),
                              builder=self.builder)

        p1_build = build.Build(repository=self.repo, slave=self.slave,
                               branch='master', named_tree='v0.1',
                               builder=self.builder)
        builds = [p_build, p1_build]
        for i, b in enumerate(builds):
            buildset = await build.BuildSet.create(repository=self.repo,
                                                   revision=self.revs[i])

            buildset.builds.append(b)
            await buildset.save()

        self.assertEqual((await self.repo.get_status()), 'ready')

    @patch.object(repository, 'repo_status_changed', Mock())
    @async_test
    async def test_check_for_status_change_not_changing(self):
        self.repo._old_status = 'running'

        @asyncio.coroutine
        def get_status():
            return 'running'

        self.repo.get_status = get_status

        await self.repo._check_for_status_change(Mock(), Mock())
        self.assertFalse(repository.repo_status_changed.send.called)

    @patch.object(repository, 'repo_status_changed', AsyncMagicMock())
    @async_test
    async def test_check_for_status_change_changing(self):
        self.repo._old_status = 'running'

        @asyncio.coroutine
        def get_status():
            return 'success'

        self.repo.get_status = get_status

        await self.repo._check_for_status_change(Mock(), Mock())
        self.assertTrue(repository.repo_status_changed.publish.called)

    @patch.object(repository, 'BuildManager', MagicMock(
        spec=repository.BuildManager, autospec=True))
    @async_test
    async def test_get_builders(self):
        await self._create_db_revisions()
        slaves = [MagicMock(spec='toxicbuild.master.slave.Slave',
                            autospec=True)]
        self.repo.build_manager.get_builders = create_autospec(
            spec=self.repo.build_manager.get_builders, mock_cls=AsyncMagicMock)
        self.repo.build_manager.get_builders.return_value = [self.builder]
        builders = await self.repo._get_builders(slaves, self.revision)
        self.assertEqual(list(builders.values())[0], [self.builder])

    @async_test
    async def test_start_build(self):
        await self._create_db_revisions()

        self.repo.add_builds_for_slave = create_autospec(
            spec=self.repo.add_builds_for_slave, mock_cls=AsyncMagicMock)
        self.repo.get_latest_revision_for_branch = create_autospec(
            spec=self.repo.get_latest_revision_for_branch,
            mock_cls=AsyncMagicMock)
        self.repo.get_latest_revision_for_branch.return_value = self.revision
        self.repo._get_builders = create_autospec(
            spec=self.repo._get_builders, mock_cls=AsyncMagicMock)

        await self.repo.start_build('master')

        self.assertTrue(self.repo.add_builds_for_slave.called)
        self.assertTrue(self.repo.get_latest_revision_for_branch.called)
        self.assertTrue(self.repo._get_builders.called)

    @async_test
    async def test_start_build_params(self):
        await self._create_db_revisions()

        self.repo.add_builds_for_slave = create_autospec(
            spec=self.repo.add_builds_for_slave, mock_cls=AsyncMagicMock)
        self.repo.get_latest_revision_for_branch = create_autospec(
            spec=self.repo.get_latest_revision_for_branch,
            mock_cls=AsyncMagicMock)
        self.repo.get_latest_revision_for_branch.return_value = self.revision
        self.repo._get_builders = create_autospec(
            spec=self.repo._get_builders, mock_cls=AsyncMagicMock)

        await self.repo.start_build('master', builder_name='builder0',
                                    named_tree='asdf', slaves=[self.slave])

        self.assertTrue(self.repo.add_builds_for_slave.called)
        self.assertFalse(self.repo.get_latest_revision_for_branch.called)
        self.assertFalse(self.repo._get_builders.called)

    @patch.object(repository, 'repo_notifications', AsyncMagicMock(
        spec=repository.repo_notifications))
    @async_test
    async def test_request_build(self):
        branch = 'master'
        named_tree = 'asfd1234'

        await self.repo.request_build(branch, named_tree=named_tree)
        self.assertTrue(repository.repo_notifications.publish.called)

    def test_add_running_build(self):
        repository.Repository.add_running_build()
        self.assertEqual(repository.Repository.get_running_builds(), 1)

    def test_remove_running_build(self):
        repository.Repository.add_running_build()
        repository.Repository.remove_running_build()
        self.assertEqual(repository.Repository.get_running_builds(), 0)

    @async_test
    async def test_cancel_build(self):
        self.repo.build_manager.cancel_build = AsyncMagicMock(
            spec=self.repo.build_manager.cancel_build)
        await self.repo.cancel_build('some-uuid')
        self.assertTrue(self.repo.build_manager.cancel_build.called)

    def test_notify_only_latest(self):
        self.repo.branches = [repository.RepositoryBranch(
            name='master', notify_only_latest=False)]
        only_latest = self.repo.notify_only_latest('master')
        self.assertFalse(only_latest)

    def test_notify_only_latest_not_known(self):
        self.repo.branches = [repository.RepositoryBranch(
            name='master', notify_only_latest=False)]
        only_latest = self.repo.notify_only_latest('dont-know')
        self.assertTrue(only_latest)

    async def _create_db_revisions(self):
        self.owner = users.User(email='zezinho@nada.co', password='123')
        await self.owner.save()
        self.repo = repository.Repository(
            name='reponame', url="git@somewhere.com/project.git",
            vcs_type='git', update_seconds=100, clone_status='ready',
            owner=self.owner)
        await self.repo.save()
        await self.repo._create_locks()

        await self.repo.save()
        rep = self.repo
        now = datetime.datetime.now()
        self.builder = await build.Builder.create(name='builder0',
                                                       repository=self.repo)
        self.slave = await slave.Slave.create(name='slave',
                                              host='localhost',
                                              port=1234,
                                              token='asdf',
                                              owner=self.owner)
        self.revs = []
        self.repo.slaves = [self.slave]
        await self.repo.save()
        for r in range(2):
            for branch in ['master', 'dev']:
                rev = repository.RepositoryRevision(
                    repository=rep, commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    author='ze',
                    title='commit {}'.format(r),
                    commit_date=now + datetime.timedelta(r))

                await rev.save()
                self.revs.append(rev)

        self.revision = repository.RepositoryRevision(repository=self.repo,
                                                      branch='master',
                                                      commit='asdf',
                                                      author='j@d.com',
                                                      title='bla',
                                                      commit_date=now)
        await self.revision.save()
        # creating another repo just to test the known branches stuff.
        self.other_repo = repository.Repository(name='bla', url='/bla/bla',
                                                update_seconds=300,
                                                vcs_type='git',
                                                owner=self.owner)
        await self.other_repo.save()

        for r in range(2):
            for branch in ['b1', 'b2']:
                rev = repository.RepositoryRevision(
                    author='ze',
                    title='commit {}'.format(r),
                    repository=self.other_repo,
                    commit='123asdf{}'.format(str(r)),
                    branch=branch,
                    commit_date=now + datetime.timedelta(r))

                await rev.save()


class RepositoryBranchTest(TestCase):

    def test_to_dict(self):
        branch = repository.RepositoryBranch(name='master')
        branch_dict = branch.to_dict()
        self.assertTrue(branch_dict['name'])


class RepositoryRevisionTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = users.User(email='a@a.com', password='bla')
        await self.user.save()
        self.repo = repository.Repository(name='bla', url='bla@bl.com/aaa',
                                          owner=self.user)
        await self.repo.save()
        self.rev = repository.RepositoryRevision(repository=self.repo,
                                                 commit='asdfasf',
                                                 branch='master',
                                                 author='ze',
                                                 title='bla',
                                                 commit_date=utils.now())
        await self.rev.save()

    @async_test
    async def tearDown(self):
        await repository.RepositoryRevision.drop_collection()
        await repository.Repository.drop_collection()
        await users.User.drop_collection()

    @async_test
    async def test_get(self):
        r = await repository.RepositoryRevision.get(
            commit='asdfasf', repository=self.repo)
        self.assertEqual(r, self.rev)

    @async_test
    async def test_to_dict(self):
        expected = {'repository_id': str(self.repo.id),
                    'commit': self.rev.commit,
                    'branch': self.rev.branch,
                    'author': self.rev.author,
                    'title': self.rev.title,
                    'commit_date': repository.utils.datetime2string(
                        self.rev.commit_date)}
        returned = await self.rev.to_dict()
        self.assertEqual(expected, returned)

    @async_test
    async def test_to_dict_external(self):
        ext = repository.ExternalRevisionIinfo(
            url='http://someurl.com/bla.git', name='other-remote',
            branch='master', into='other-remote:master')
        self.rev.external = ext
        await self.rev.save()
        expected = {'repository_id': str(self.repo.id),
                    'commit': self.rev.commit,
                    'branch': self.rev.branch,
                    'author': self.rev.author,
                    'title': self.rev.title,
                    'commit_date': repository.utils.datetime2string(
                        self.rev.commit_date),
                    'external': {'branch': 'master',
                                 'name': 'other-remote',
                                 'url': 'http://someurl.com/bla.git',
                                 'into': 'other-remote:master'}}
        returned = await self.rev.to_dict()
        self.assertEqual(expected, returned)

    def test_check_skip(self):
        self.rev.body = 'some body\nhey you ci: skip please'
        self.assertFalse(self.rev.create_builds())

    def test_check_skip_dont_skip(self):
        self.rev.body = 'some body\n'
        self.assertTrue(self.rev.create_builds())
