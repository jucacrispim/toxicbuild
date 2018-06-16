# -*- coding: utf-8 -*-
# Copyright toxicbuild Juca Crispim <juca@poraodojuca.net>

# This file is part of 2018.

# 2018 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# 2018 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with 2018. If not, see <http://www.gnu.org/licenses/>.

import time
from aiozk import ZKClient
from aiozk.exc import TimeoutError, SessionLost
from aiozk.recipes.shared_lock import SharedLock
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master import settings


class ToxicSharedLock(SharedLock):
    """This class is just to patch the original one to correct a bug
    with the acquire timeout. I oppend a
    `PR <https://github.com/tipsi/aiozk/pull/22>` to fix that. It it
    gets approved, when the a new version is released with that this
    thing must be removed."""

    async def wait_in_line(self, znode_label, timeout=None, blocked_by=None):
        time_limit = None
        if timeout is not None:
            time_limit = time.time() + timeout

        await self.create_unique_znode(znode_label)

        while True:
            if time_limit and time.time() >= time_limit:
                raise TimeoutError

            owned_positions, contenders = await self.analyze_siblings()
            if znode_label not in owned_positions:  # pragma no cover
                raise SessionLost

            blockers = contenders[:owned_positions[znode_label]]
            if blocked_by:
                blockers = [
                    contender for contender in blockers
                    if self.determine_znode_label(contender) in blocked_by
                ]

            if not blockers:
                break

            try:
                await self.wait_on_sibling(blockers[-1], timeout)
            except TimeoutError:
                await self.delete_unique_znode(znode_label)

        return self.make_contextmanager(znode_label)


class ToxicZKClient(LoggerMixin):
    _zk_client = None

    def __init__(self):
        if not self._client:
            servers = ','.join(settings.ZK_SERVERS)
            kwargs = getattr(settings, 'ZK_KWARGS', {})
            client = ZKClient(servers, **kwargs)
            self._client = client
        self._started = False

    def _get_client(self):
        return type(self)._zk_client

    def _set_client(self, client):
        type(self)._zk_client = client

    async def _start(self):
        await self._client.start()

    async def get_lock(self, path):
        if not self._started:  # pragma no branch
            await self._start()
        recipe = ToxicSharedLock(path)
        recipe.set_client(self._client)
        return recipe

    _client = property(_get_client, _set_client)


class Lock(LoggerMixin):

    def __init__(self, path):
        self.path = path
        self.client = ToxicZKClient()

    async def acquire_read(self, timeout=None):
        lock_inst = await self.client.get_lock(self.path)
        return await lock_inst.acquire_read(timeout=timeout)

    async def acquire_write(self, timeout=None):
        lock_inst = await self.client.get_lock(self.path)
        return await lock_inst.acquire_write(timeout=timeout)
