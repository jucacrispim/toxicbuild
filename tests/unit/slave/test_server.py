# -*- coding: utf-8 -*-

# Copyright 2015, 2018 Juca Crispim <juca@poraodojuca.net>

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
import unittest
from unittest.mock import MagicMock, patch
from toxicbuild.slave import server
from tests import async_test, AsyncMagicMock


class BuildServerTest(unittest.TestCase):

    @patch.object(asyncio, 'get_event_loop', MagicMock())
    def setUp(self):
        self.buildserver = server.BuildServer(addr='127.0.0.1', port=1234)

    @patch.object(server.asyncio, 'sleep', AsyncMagicMock(
        spec=server.asyncio.sleep))
    @async_test
    async def test_shutdown(self):

        self.called = False

        async def sleep(n):
            self.buildserver.PROTOCOL_CLS._clients_connected -= 1
            self.called = True

        server.asyncio.sleep = sleep
        self.buildserver.PROTOCOL_CLS._clients_connected = 1
        await self.buildserver.shutdown()
        self.assertTrue(self.called)
