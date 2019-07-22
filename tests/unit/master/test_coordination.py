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

from aiozk.exc import TimeoutError
from unittest import TestCase
from toxicbuild.master import coordination
from tests import async_test


class ToxicLocksTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.lock_carrier = coordination.Lock('/path')

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await cls.lock_carrier.client._client.delete('/path')

    @async_test
    async def test_acquire_write_lock(self):
        lock = await self.lock_carrier.acquire_write()
        self.GOT_LOCK = False
        async with lock:
            self.GOT_LOCK = True
            with self.assertRaises(TimeoutError):
                await coordination.Lock('/path').acquire_write(timeout=0.1)

        self.assertTrue(self.GOT_LOCK)

        self.GOT_AGAIN = False
        lock = await self.lock_carrier.acquire_write()
        async with lock:
            self.GOT_AGAIN = True

        self.assertTrue(self.GOT_AGAIN)

    @async_test
    async def test_acquire_read_lock(self):
        self.GOT_IT = False
        async with await self.lock_carrier.acquire_read():
            self.GOT_IT = True

        self.assertTrue(self.GOT_IT)
