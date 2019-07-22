# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

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

from unittest import TestCase
from toxicbuild.common import utils
from toxicbuild.core.utils import now, localtime2utc


class UtilsTest(TestCase):

    def test_is_datetime(self):
        dtstr = '3 10 25 06:50:49 2017 +0000'
        self.assertTrue(utils.is_datetime(dtstr))

    def test_is_datetime_not_dt(self):
        dtstr = 'some-thing'
        self.assertFalse(utils.is_datetime(dtstr))

    def test_is_datetime_not_str(self):
        self.assertFalse(utils.is_datetime(1))

    def test_get_timezone(self):
        tz = utils._get_timezone('America/Sao_Paulo')
        self.assertEqual(tz.zone, 'America/Sao_Paulo')

    def test_get_timezone_bad_timezone(self):
        tz = utils._get_timezone('Bogus')
        self.assertIsNone(tz)

    def test_get_timezone_no_settings(self):
        tz = utils._get_timezone(None)
        self.assertIsNone(tz)

    def test_format_datetime_no_dtformat(self):
        dt = localtime2utc(now())
        formated = utils.format_datetime(dt, '%s', tzname='America/Sao_Paulo')
        self.assertFalse(formated.endswith('0000'))

    def test_format_datetime(self):
        dt = localtime2utc(now())
        dtformat = '%z'
        formated = utils.format_datetime(dt, dtformat)
        self.assertEqual(formated, '+0000')

    def test_format_datetime_with_tzname(self):
        dtformat = '%z'
        dt = localtime2utc(now())
        formated = utils.format_datetime(
            dt, dtformat, tzname='America/Sao_Paulo')
        self.assertFalse(formated.endswith('0000'))

    def test_format_datetime_bad_tz(self):
        dtformat = '%z'
        dt = localtime2utc(now())
        formated = utils.format_datetime(
            dt, dtformat, tzname='America/SSao_Paulo')
        self.assertTrue(formated.endswith('0000'))
