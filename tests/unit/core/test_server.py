# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from unittest import TestCase
from unittest.mock import Mock, patch

from toxicbuild.core import server

from tests import AsyncMagicMock


class ToxicServerTest(TestCase):

    @patch('asyncio.events.AbstractEventLoop.create_server', AsyncMagicMock())
    def setUp(self):
        loop = Mock()
        self.server = server.ToxicServer('0.0.0.0', 8888, loop=loop)

    def test_get_protocol_instance(self):
        prot = self.server.get_protocol_instance()
        self.assertIsInstance(prot, self.server.PROTOCOL_CLS)

    @patch.object(server.ssl, 'create_default_context', Mock(
        spec=server.ssl.create_default_context))
    def test_instance_ssl(self):
        loop = Mock()
        self.server = server.ToxicServer('0.0.0.0', 8888, loop=loop,
                                         use_ssl=True, ssl_kw={})
        self.assertTrue(server.ssl.create_default_context.called)

    def test_context_management(self):
        self.server.loop.run_until_complete = asyncio.get_event_loop()\
                                                     .run_until_complete
        self.server.server = Mock(spec=self.server.server,
                                  close=Mock(),
                                  wait_closed=AsyncMagicMock())

        with self.server:
            pass

        self.assertTrue(self.server.server.close.called)
        self.assertTrue(self.server.server.wait_closed.called)

    def test_start(self):
        self.server.loop.run_forever = Mock(spec=self.server.loop.run_forever)
        self.server.sync_shutdown = Mock(spec=self.server.sync_shutdown)

        self.server.start()

        self.assertTrue(self.server.loop.run_forever.called)
        self.assertTrue(self.server.sync_shutdown.called)
