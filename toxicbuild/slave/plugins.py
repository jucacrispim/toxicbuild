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
import os
from toxicbuild.slave.exceptions import PluginNotFound
from toxicbuild.slave.build import BuildStep


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


class PythonCreateVenvStep(BuildStep):

    """Step that checks if the venv already exists before
    executing the command."""

    def __init__(self, venv_dir, pyversion):
        self.venv_dir = venv_dir
        self.pyversion = pyversion
        name = 'Create virtualenv'
        command = 'virtualenv {} -p {}'.format(self.venv_dir,
                                               self.pyversion)
        super().__init__(name, command, stop_on_fail=True)

    @asyncio.coroutine
    def execute(self, cwd, **envvars):
        pyexec = os.path.join(self.venv_dir, os.path.join('bin', 'python'))
        if os.path.exists(os.path.join(cwd, pyexec)):
            step_info = {'status': 'success',
                         'output': 'venv exists. Skipping...'}
        else:
            step_info = yield from super().execute(cwd, **envvars)

        return step_info


class PythonVenvPlugin(Plugin):
    name = 'python-venv'

    def __init__(self, pyversion, requirements_file='requirements.txt',
                 remove_env=False):
        self.pyversion = pyversion
        self.requirements_file = requirements_file
        self.remove_env = remove_env
        self.venv_dir = 'venv-{}'.format(self.pyversion.replace(os.sep, ''))

    def get_steps_before(self):
        create_env = PythonCreateVenvStep(self.venv_dir, self.pyversion)

        install_deps = BuildStep('install dependencies using pip',
                                 'pip install -r {}'.format(
                                     self.requirements_file),
                                 stop_on_fail=True)

        return [create_env, install_deps]

    def get_steps_after(self):
        steps = []
        if self.remove_env:
            steps.append(BuildStep('remove venv',
                                   'rm -rf {}'.format(self.venv_dir)))
        return steps

    def get_env_vars(self):
        return {'PATH': '{}/bin:PATH'.format(self.venv_dir)}
