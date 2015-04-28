# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
import unittest
from unittest.mock import MagicMock, patch
from toxicbuild.slave import protocols, server


class BuildServerTest(unittest.TestCase):
    @classmethod
    @patch.object(asyncio, 'get_event_loop', MagicMock())
    def setUpClass(cls):
        cls.buildserver = server.BuildServer(addr='127.0.0.1', port=1234)

    def test_instanciation(self):
        self.assertTrue(self.buildserver.loop.create_server.called)

    def test_get_protocol_instance(self):
        self.assertTrue(isinstance(self.buildserver.get_protocol_instance(),
                                   protocols.BuildServerProtocol))

    def test_start(self):
        self.buildserver.start()
        self.assertTrue(self.buildserver.loop.run_forever.called)

    def test_context_manager(self):
        with self.buildserver as inst:
            self.assertTrue(isinstance(inst, server.BuildServer))

        self.assertTrue(self.buildserver.loop.close.called)

    @patch.object(server, 'BuildServer', MagicMock())
    def test_runserver(self):
        server.run_server()

        server_inst = server.BuildServer.return_value.__enter__.return_value

        self.assertTrue(server_inst.start.called)
