# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from unittest.mock import patch, Mock
from toxicbuild.core import cmd


@patch('mando.Program._generate_command')
@patch('mando.Program.execute')
@patch('mando.Program.__call__')
class ToxicProgramTest(TestCase):

    def test_generate_command(self, *args, **kwargs):
        cmd.main._generate_command()
        self.assertEqual(len(cmd.main._generate_queue), 1)

    def test_execute(self, *args, **kwargs):
        gen = Mock()
        cmd.main._generate_queue = [gen]
        cmd.main.execute()
        self.assertTrue(gen.called)

    @patch.object(cmd.sys, 'argv', Mock())
    def test_call_with_one_arg(self, *args, **kwargs):
        cmd.sys.argv = ['somecommand']
        cmd.main()
        self.assertEqual(cmd.sys.argv[-1], '-h')

    @patch.object(cmd.sys, 'argv', Mock())
    def test_call_with_two_args_command(self, *args, **kwargs):
        cmd.sys.argv = ['somecommand', 'start']
        cmd.main()
        self.assertEqual(cmd.sys.argv[-1], '-h')

    @patch.object(cmd.sys, 'argv', Mock())
    def test_call_with_two_args_not_command(self, *args, **kwargs):
        cmd.sys.argv = ['somecommand', 'action']
        cmd.main()
        self.assertEqual(cmd.sys.argv[-1], 'action')
