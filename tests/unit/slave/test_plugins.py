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

import unittest
from toxicbuild.slave import plugins


class MyPlugin(plugins.Plugin):
    name = 'my-plugin'


class PluginTest(unittest.TestCase):

    def setUp(self):
        self.plugin = MyPlugin()

    def test_get(self):

        plugin = plugins.Plugin.get('my-plugin')
        self.assertEqual(plugin, type(self.plugin))

    def test_get_without_a_plugin(self):
        with self.assertRaises(plugins.PluginNotFound):
            plugins.Plugin.get('i-dont-exist')

    def test_get_steps_before(self):
        self.assertEqual([], self.plugin.get_steps_before())

    def test_get_steps_after(self):
        self.assertEqual([], self.plugin.get_steps_after())

    def test_get_env_vars(self):
        self.assertEqual({}, self.plugin.get_env_vars())


class PythonVenvPluginTest(unittest.TestCase):

    def setUp(self):
        self.plugin = plugins.PythonVenvPlugin(pyversion='/usr/bin/python3.4')

    def test_name(self):
        self.assertEqual(self.plugin.name, 'python-venv')

    def test_get_steps_before(self):
        expected = [
            {'name': 'create venv',
             'command': 'virtualenv venv -p /usr/bin/python3.4'},
            {'name': 'install dependencies using pip',
             'command': 'pip install -r requirements.txt'}
        ]

        steps_before = self.plugin.get_steps_before()

        self.assertEqual(expected, steps_before)

    def test_get_steps_after_without_remove(self):
        expected = []
        steps_after = self.plugin.get_steps_after()

        self.assertEqual(expected, steps_after)

    def test_get_steps_after_removing(self):
        expected = [{'name': 'remove-env', 'command': 'rm -rf venv'}]
        self.plugin.remove_env = True
        steps_after = self.plugin.get_steps_after()

        self.assertEqual(expected, steps_after)

    def test_get_env_vars(self):
        expected = {'PATH': 'PATH:venv/bin'}
        env_vars = self.plugin.get_env_vars()

        self.assertEqual(expected, env_vars)
