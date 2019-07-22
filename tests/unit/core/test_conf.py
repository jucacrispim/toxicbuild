# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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


import unittest
from unittest import mock
from toxicbuild.core import conf
from tests.unit.core import TEST_DATA_DIR


@mock.patch.object(conf.os, 'environ', {})
class SettingsTest(unittest.TestCase):

    @mock.patch.object(conf.os, 'environ', {})
    def setUp(self):
        settingsfile = conf.os.path.join(TEST_DATA_DIR, 'toxicbuild.conf')
        self.settingsfile = settingsfile
        self.settings = conf.Settings('SETTINGS_ENVVAR', self.settingsfile)

    def test_filename(self):
        # first without environ variable
        fname = self.settings._filename
        self.assertEqual(fname, self.settingsfile)

        # now with a environ var
        conf.os.environ.update(
            {'SETTINGS_ENVVAR': '/some/path/to/settings.conf'})

        fname = self.settings._filename
        self.assertEqual(fname, '/some/path/to/settings.conf')

    def test_settings(self):
        conf.os.environ = {}

        # everything ok
        self.assertEqual(self.settings.BLA, 'val')

        # this does not exist
        with self.assertRaises(AttributeError):
            self.settings.BLE

        # and now trying to set
        with self.assertRaises(AttributeError):
            self.settings.BLA = 'oi'
