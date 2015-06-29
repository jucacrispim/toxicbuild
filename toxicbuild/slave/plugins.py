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

from toxicbuild.slave.exceptions import PluginNotFound


class Plugin:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    # Your plugin must have an unique name
    name = 'BasePlugin'

    @classmethod
    def get(cls, name):
        """ Returns a Plugin subclass based on its name."""

        for plugin in cls.__subclasses__():
            if plugin.name == name:
                return plugin
        raise PluginNotFound('Plugin {} does not exist.'.format(name))

    def get_steps_before(self):
        """Returns a list of steps to be executed before the steps provided
        by the user."""

        return []

    def get_steps_after(self):
        """Returns a list of steps to be executed after the steps provided
        by the user."""

        return []

    def get_env_vars(self):
        """ Returns a dictionary containing values for environment
        variables."""

        return {}


class PythonVenvPlugin(Plugin):
    name = 'python-venv'

    def __init__(self, pyversion, requirements_file='requirements.txt',
                 remove_env=False):
        self.pyversion = pyversion
        self.requirements_file = requirements_file
        self.remove_env = remove_env

    def get_steps_before(self):
        create_env = {'name': 'create venv',
                      'command': 'virtualenv venv -p {}'.format(
                          self.pyversion)}

        install_deps = {'name': 'install dependencies using pip',
                        'command': 'pip install -r {}'.format(
                            self.requirements_file)}

        return [create_env, install_deps]

    def get_steps_after(self):
        steps = []
        if self.remove_env:
            steps.append({'name': 'remove-env',
                          'command': 'rm -rf venv'})
        return steps

    def get_env_vars(self):
        return {'PATH': 'PATH:venv/bin'}
