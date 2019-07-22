# -*- coding: utf-8 -*-

# Copyright 2016-2018 Juca Crispim <juca@poraodojuca.net>

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

from toxicbuild.core.exceptions import PluginNotFound


class PluginMeta(type):

    def __new__(cls, name, bases, attrs):
        no_list = attrs.get('no_list')
        r = super().__new__(cls, name, bases, attrs)
        if no_list is None:
            setattr(r, 'no_list', False)
        return r


class Plugin(metaclass=PluginMeta):
    """This is a base plugin. Plugins may implement aditional behavior
    to your builds."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Your plugin must have an unique name
    name = 'BaseCorePlugin'

    @classmethod
    def list_plugins(cls, plugin_type=None):
        """Returns a list of Plugin subclasses.

        :param plugin_type: the plugin's type."""
        plugins = []
        for plugin in cls.__subclasses__():
            plugins += plugin.list_plugins(plugin_type=plugin_type)

        return plugins + [p for p in cls.__subclasses__() if not p.no_list]

    @classmethod
    def get_plugin(cls, name):
        """ Returns a Plugin subclass based on its name.

        :param name: Plugin's name."""

        for plugin in cls.__subclasses__():
            try:
                return plugin.get_plugin(name)
            except PluginNotFound:
                pass

            if plugin.name == name:
                return plugin

        raise PluginNotFound('Plugin {} does not exist.'.format(name))
