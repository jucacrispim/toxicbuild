# -*- coding: utf-8 -*-

# Copyright 2016 Juca Crispim <juca@poraodojuca.net>

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

from toxicbuild.core.exceptions import PluginNotFound


class Plugin:
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

        return cls.__subclasses__()

    @classmethod
    def get_plugin(cls, name):
        """ Returns a Plugin subclass based on its name.

        :param name: Plugin's name."""

        for plugin in cls.__subclasses__():
            if plugin.name == name:
                return plugin

        raise PluginNotFound('Plugin {} does not exist.'.format(name))
