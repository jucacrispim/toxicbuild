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

from unittest import TestCase
from unittest.mock import MagicMock, patch

from toxicbuild.ui.console import commands

from tests import async_test, AsyncMagicMock


class ConsoleCommandTest(TestCase):

    def setUp(self):
        self.command = commands.ConsoleCommand(MagicMock())

    def test_get_help(self):
        self.command.help_text = 'A text'
        r = self.command.get_help()
        self.assertEqual(r, self.command.help_text)

    def test_get_params(self):
        self.command.params = {'bla': 1}
        r = self.command.get_params()
        self.assertTrue(r['bla'])

    def test_get_name(self):
        self.command.name = 'ble'
        r = self.command.get_name()
        self.assertEqual(r, self.command.name)

    @async_test
    async def test_execute(self):
        with self.assertRaises(NotImplementedError):
            await self.command.execute()


class RepoListCommandTest(TestCase):

    def setUp(self):
        self.command = commands.RepoListCommand(MagicMock())

    @patch.object(commands.RepositoryInterface, 'list',
                  AsyncMagicMock(spec=commands.RepositoryInterface.list))
    @async_test
    async def test_execute(self):
        await self.command.execute()
        self.assertTrue(commands.RepositoryInterface.list.called)
