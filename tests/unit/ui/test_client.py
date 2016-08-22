# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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
from unittest import TestCase
from unittest.mock import MagicMock, patch
from toxicbuild.ui.client import UIHoleClient, get_hole_client
from tests import async_test


class UIHoleClientTest(TestCase):

    @patch.object(UIHoleClient, 'get_response', MagicMock())
    @patch.object(UIHoleClient, 'write', MagicMock())
    @async_test
    def test_request2server(self):
        client = UIHoleClient('localhost', 7777)
        client.get_response = asyncio.coroutine(
            lambda: {'body': {'action': 'uhu!'}})

        response = yield from client.request2server('action', {})
        self.assertEqual(response, 'uhu!')

    @patch.object(UIHoleClient, 'request2server', MagicMock())
    @async_test
    def test_getattr(self):
        client = UIHoleClient('localhost', 7777)
        yield from client.test()

        self.assertTrue(client.request2server.called)

    @patch.object(UIHoleClient, 'connect', MagicMock())
    @async_test
    def test_get_hole_client(self):
        client = yield from get_hole_client('localhost', 7777)
        self.assertTrue(client.connect.called)
