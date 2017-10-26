# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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
from unittest.mock import Mock, patch
from toxicbuild.core.utils import now, localtime2utc
from toxicbuild.ui import utils


class UtilsDateTimeTest(TestCase):

    @patch.object(utils, 'settings', Mock())
    def test_get_dtformat(self):
        utils.settings.DTFORMAT = '%y %a'
        returned = utils._get_dtformat()
        self.assertEqual(returned, utils.settings.DTFORMAT)

    def test_get_dtformat_no_settings(self):
        returned = utils._get_dtformat()
        self.assertEqual(returned, utils.DTFORMAT)

    @patch.object(utils, 'settings', Mock())
    def test_get_timezone(self):
        utils.settings.TIMEZONE = 'America/Sao_Paulo'
        tz = utils._get_timezone()
        self.assertEqual(tz.zone, 'America/Sao_Paulo')

    @patch.object(utils, 'settings', Mock())
    def test_get_timezone_bad_timezone(self):
        utils.settings.TIMEZONE = 'Bogus'
        tz = utils._get_timezone()
        self.assertIsNone(tz)

    def test_get_timezone_no_settings(self):
        tz = utils._get_timezone()
        self.assertIsNone(tz)

    @patch.object(utils, 'settings', Mock())
    def test_format_datetime(self):
        utils.settings.TIMEZONE = 'America/Sao_Paulo'
        utils.settings.DTFORMAT = utils.DTFORMAT
        dt = localtime2utc(now())
        formated = utils.format_datetime(dt)
        self.assertFalse(formated.endswith('0000'))

    @patch.object(utils, 'settings', Mock())
    def test_format_datetime_bad_tz(self):
        utils.settings.TIMEZONE = 'America/SSao_Paulo'
        utils.settings.DTFORMAT = utils.DTFORMAT
        dt = localtime2utc(now())
        formated = utils.format_datetime(dt)
        self.assertTrue(formated.endswith('0000'))

    def test_is_datetime(self):
        dtstr = 'Wed Oct 25 06:50:49 2017 +0000'
        self.assertTrue(utils.is_datetime(dtstr))

    def test_is_datetime_not_dt(self):
        dtstr = 'some-thing'
        self.assertFalse(utils.is_datetime(dtstr))

    def test_is_datetime_not_str(self):
        self.assertFalse(utils.is_datetime(1))
