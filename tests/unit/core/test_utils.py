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


import os
import tornado
from tornado.testing import AsyncTestCase, gen_test
from toxicbuild.core import utils
from tests.unit.core import TEST_DATA_DIR


class ExecCmdTest(AsyncTestCase):

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()

    @gen_test
    def test_exec_cmd(self):

        # no assertions here because if no exceptions, it's ok.
        yield from utils.exec_cmd('ls', cwd='.')

    @gen_test
    def test_exec_cmd_with_error(self):

        with self.assertRaises(utils.ExecCmdError):
            # please, don't tell me you have a lsz command on your system.
            yield from utils.exec_cmd('lsz', cwd='.')

    def test_load_module_from_file_with_file_not_found(self):
        with self.assertRaises(FileNotFoundError):
            utils.load_module_from_file('/some/file/that/does/not/exist.conf')

    def test_load_module_from_file_with_some_error(self):
        filename = os.path.join(TEST_DATA_DIR, 'toxicbuild_error.conf')

        with self.assertRaises(utils.ConfigError):
            utils.load_module_from_file(filename)

    def test_load_module_from_file(self):
        filename = os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
        mod = utils.load_module_from_file(filename)

        self.assertEqual(mod.BLA, 'val')
