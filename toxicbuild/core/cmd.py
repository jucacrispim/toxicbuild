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

from functools import partial
import sys
from mando import Program


class ToxicProgram(Program):

    """Transforms a python function into a command line program.
    Extends mando's Program to execute _generate_command() only
    when execute() is called to enable toxicbuild command hacks."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._generate_queue = []

    def _generate_command(self, *args, **kwargs):
        super_gen = super()._generate_command
        call = partial(super_gen, *args, **kwargs)
        self._generate_queue.append(call)

        if len(args) == 1 and hasattr(args[0], '__call__'):
            return args[0]
        else:
            def _command(func):  # pragma no cover
                return func
            return _command

    def execute(self, *args, **kwargs):
        [call() for call in self._generate_queue]
        super().execute(*args, **kwargs)
        self._generate_queue = []

    def __call__(self):
        cmds = ['start', 'stop', 'create', 'restart']

        if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in cmds):
            sys.argv.append('-h')

        super().__call__()


main = ToxicProgram()
command = main.command
arg = main.arg
parse = main.parse
execute = main.execute
