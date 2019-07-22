# -*- coding: utf-8 -*-
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
import signal
from aioamqp.exceptions import AmqpClosedConnection
from asyncamqp.exceptions import ConsumerTimeout
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master.exchanges import (
    repo_notifications,
    revisions_added,
    connect_exchanges
)
from toxicbuild.master.repository import Repository, RepositoryRevision


__doc__ = """This module implements consumers for messages published
in exchanges. The consumer react (call something) in response for a
incomming message."""


class BaseConsumer(LoggerMixin):
    """A base class for the consumer that react to incomming messages
    from exchanges"""

    def __init__(self, exchange, msg_callback, routing_key=None, loop=None):
        """:param exchange: The exchange in which messages are published
          for the consumer to fetch.
        :param msg_callback: A callable that receives the message.
        :param routing_key: The routing key to consume messages.
        """

        self.exchange = exchange
        self.msg_callback = msg_callback
        self.routing_key = routing_key
        self.loop = loop or asyncio.get_event_loop()
        self._stop = False
        self._running_tasks = 0
        signal.signal(signal.SIGTERM, self.sync_shutdown)

    async def run(self):
        """Starts the consumer."""

        kw = {'timeout': 1000}
        if self.routing_key:
            kw['routing_key'] = self.routing_key

        async with await self.exchange.consume(**kw) as consumer:
            while not self._stop:
                try:
                    msg = await consumer.fetch_message(cancel_on_timeout=False)
                except ConsumerTimeout:
                    continue
                except AmqpClosedConnection:
                    self.log('AmqpClosedConnection. Trying again...',
                             level='error')
                    await connect_exchanges()
                    continue

                self.log('Consuming message')

                asyncio.ensure_future(self.msg_callback(msg))
                await msg.acknowledge()

            self._stop = False

    def stop(self):
        self._stop = True

    async def shutdown(self):
        self.log('Shutting down')
        self.stop()
        while self._running_tasks > 0:
            self.log('Waiting for tasks')
            await asyncio.sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        self.loop.run_until_complete(self.shutdown())


class RepositoryMessageConsumer(LoggerMixin):
    """Waits for messages published in the ``repo_notifications``
    exchange and reacts to them."""

    REPOSITORY_CLASS = Repository
    REPOSITORY_REVISION_CLASS = RepositoryRevision

    revision_consumer = None
    build_consumer = None
    removal_consumer = None
    update_consumer = None

    def __init__(self):
        type(self).revision_consumer = BaseConsumer(revisions_added,
                                                    self._add_builds)
        type(self).build_consumer = BaseConsumer(repo_notifications,
                                                 self._add_requested_build,
                                                 routing_key='build-requested')
        type(self).removal_consumer = BaseConsumer(
            repo_notifications, self._remove_repo,
            routing_key='repo-removal-requested')
        type(self).update_consumer = BaseConsumer(
            repo_notifications, self._update_repo,
            routing_key='update-code-requested')

    def run(self):
        """Starts the repository message consumer.
        """
        self.log('[init] Waiting revisions')
        asyncio.ensure_future(type(self).revision_consumer.run())
        self.log('[init] Waiting build requests')
        asyncio.ensure_future(type(self).build_consumer.run())
        self.log('[init] Waiting removal requests')
        asyncio.ensure_future(type(self).removal_consumer.run())
        self.log('[init] Waiting code update requests')
        asyncio.ensure_future(type(self).update_consumer.run())

    async def _get_repo_from_msg(self, msg):
        try:
            repo = await self.REPOSITORY_CLASS.get(
                id=msg.body['repository_id'])
        except Repository.DoesNotExist:
            log_msg = '[_get_repo_from_msg] repo {} does not exist'.format(
                msg.body['repository_id'])
            self.log(log_msg, level='warning')
            return

        return repo

    async def _add_builds(self, msg):
        repo = await self._get_repo_from_msg(msg)
        if not repo:
            return

        body = msg.body
        try:
            revisions = await self.REPOSITORY_REVISION_CLASS.objects.filter(
                id__in=body['revisions_ids']).to_list()

            await repo.build_manager.add_builds(revisions)
        except Exception as e:
            log_msg = 'Error adding builds for repo {}. '.format(repo.id)
            log_msg += 'Exception was {}'.format(str(e))
            self.log(log_msg, level='error')

    async def _add_requested_build(self, msg):
        repo = await self._get_repo_from_msg(msg)
        if not repo:
            return

        body = msg.body
        try:
            branch = body['branch']
            builder_name = body.get('builder_name')
            named_tree = body.get('named_tree')

            await repo.start_build(branch, builder_name=builder_name,
                                   named_tree=named_tree)
        except Exception as e:
            log_msg = 'Error starting builds for {}. '.format(repo.id)
            log_msg += 'Exception was {}'.format(str(e))
            self.log(log_msg, level='error')

    async def _remove_repo(self, msg):
        repo = await self._get_repo_from_msg(msg)
        if not repo:
            return False
        try:
            await repo.remove()
        except Exception as e:
            log_msg = '[_remove_repo] Error removing repo {}'.format(repo.id)
            log_msg += '\nOriginal exception was {}'.format(str(e))
            self.log(log_msg, level='error')

        return True

    async def _update_repo(self, msg):
        repo = await self._get_repo_from_msg(msg)
        repo_branches = msg.body.get('repo_branches')
        external = msg.body.get('external')
        wait_for_lock = msg.body.get('wait_for_lock', False)
        kw = {'repo_branches': repo_branches,
              'external': external,
              'wait_for_lock': wait_for_lock}
        if not repo:
            return False
        try:
            await repo.update_code(**kw)
        except Exception as e:
            log_msg = '[_update_repo] Error update repo {}'.format(repo.id)
            log_msg += '\nOriginal exception was {}'.format(str(e))
            self.log(log_msg, level='error')

        return True

    @classmethod
    def stop(cls):
        cls.revision_consumer.stop()
        cls.build_consumer.stop()
        cls.removal_consumer.stop()
        cls.update_consumer.stop()
