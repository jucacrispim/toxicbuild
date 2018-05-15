# -*- coding: utf-8 -*-

# Copyright 2016-2018 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from toxicbuild.core import plugins


class BasePlugin(plugins.Plugin):
    pass


class MyPlugin(BasePlugin):
    name = 'my-plugin'


class MyOtherPlugin(BasePlugin):
    name = 'other-plugin'
    type = 'test'


class MySubPlugin(MyPlugin):
    name = 'sub-plugin'


class SomeBasePlugin(BasePlugin):
    name = 'base'
    no_list = True


class SomeOtherPlugin(SomeBasePlugin):
    name = 'the-actual-plugin'


class PluginTest(TestCase):

    def setUp(self):
        self.plugin = MyPlugin()

    def test_list_plugins(self):
        plugins_list = BasePlugin.list_plugins()
        self.assertEqual(len(plugins_list), 4)

    def test_get_plugin(self):

        plugin = BasePlugin.get_plugin('my-plugin')
        self.assertEqual(plugin, type(self.plugin))

    def test_get_without_a_plugin(self):
        with self.assertRaises(plugins.PluginNotFound):
            plugins.Plugin.get_plugin('i-dont-exist')
