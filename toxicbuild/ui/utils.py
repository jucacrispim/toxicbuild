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

import re
import pytz
from toxicbuild.core.conf import ConfigError
from toxicbuild.core.utils import DTFORMAT, datetime2string
from toxicbuild.ui import settings


_dt_regex = re.compile('\w+\s\w+\s\d+\s\d+:\d+:\d+\s\d+\s[\+|-]\d+$')


def _get_dtformat():
    try:
        dtformat = settings.DTFORMAT
    except ConfigError:
        dtformat = DTFORMAT

    return dtformat


def _get_timezone():
    try:
        tz = settings.TIMEZONE
        tz = pytz.timezone(tz)
    except (ConfigError, pytz.UnknownTimeZoneError):
        tz = None

    return tz


def format_datetime(dt):
    """Formats a datetime object according to the
    timezone and format specified in the config file.

    :param dt: A datetime object."""

    dtformat = _get_dtformat()
    tz = _get_timezone()

    if tz:
        dt = dt.astimezone(tz)

    return datetime2string(dt, dtformat=dtformat)


def is_datetime(dtstr):
    """Checks if a string is a formated datetime.
    The format expected for the datetime string is:
    '%a %b %d %H:%M:%S %Y %z'"""

    if not isinstance(dtstr, str):
        return False
    return bool(re.match(_dt_regex, dtstr))
