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


from aiozk import ZKClient
from aiozk.recipes.shared_lock import SharedLock
from toxicbuild.core.utils import LoggerMixin


class ToxicZKClient(LoggerMixin):
    settings = None

    _zk_client = None
    _started = False

    # The lock paths that where already created in the process.
    # This is here so we don't need to call create every time.
    _created_paths = {}

    def __init__(self):
        if not self._client:
            servers = ','.join(self.settings.ZK_SERVERS)
            kwargs = getattr(self.settings, 'ZK_KWARGS', {})
            client = ZKClient(servers, **kwargs)
            self._client = client

    def _get_client(self):
        return type(self)._zk_client

    def _set_client(self, client):
        type(self)._zk_client = client

    async def _start(self):
        await self._client.start()
        type(self)._started = True

    async def get_lock(self, path):
        if not self._started:  # pragma no branch
            await self._start()
        recipe = SharedLock(path)
        recipe.set_client(self._client)
        await self._create_path(recipe)
        return recipe

    async def _create_path(self, recipe):
        if not type(self)._created_paths.get(recipe.base_path):
            await recipe.create_znode(recipe.base_path)
            type(self)._created_paths[recipe.base_path] = True

    _client = property(_get_client, _set_client)


class LockContext:

    def __init__(self, lock, timeout=None):
        self.lock = lock
        self.timeout = timeout
        self._acquired = False

    async def __aenter__(self):
        if not self._acquired:
            await self.acquire()  # pragma no cover

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.lock.release()

    async def acquire(self):
        if self.timeout:
            lock = await self.lock.acquire(timeout=self.timeout)
        else:
            lock = await self.lock.__aenter__()

        self._acquired = True
        return lock


class Lock(LoggerMixin):

    def __init__(self, path):
        self.path = path
        self.client = ToxicZKClient()

    async def acquire_read(self, timeout=None):
        lock_inst = await self.client.get_lock(self.path)
        ctx = LockContext(lock_inst.reader_lock, timeout)
        await ctx.acquire()
        return ctx

    async def acquire_write(self, timeout=None):
        lock_inst = await self.client.get_lock(self.path)
        ctx = LockContext(lock_inst.writer_lock, timeout)
        await ctx.acquire()
        return ctx
