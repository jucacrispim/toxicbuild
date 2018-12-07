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

from http.cookies import Morsel
import re
import pytz

from toxicbuild.core.utils import DTFORMAT, datetime2string
from toxicbuild.ui import settings


_dt_regex = re.compile('\d\s\d+\s\d+\s\d+:\d+:\d+\s\d+\s[\+|-]\d+$')


def _get_dtformat():
    try:
        dtformat = settings.DTFORMAT
    except AttributeError:
        dtformat = DTFORMAT

    return dtformat


def _get_timezone():
    try:
        tz = settings.TIMEZONE
        tz = pytz.timezone(tz)
    except (AttributeError, pytz.UnknownTimeZoneError):
        tz = None

    return tz


def format_datetime(dt, dtformat=None):
    """Formats a datetime object according to the
    timezone and format specified in the config file.

    :param dt: A datetime object.
    :param dtformat: The format for the datetime."""

    if not dtformat:
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


def get_client_settings():
    """Returns the settings that must be used by the client"""
    host = settings.HOLE_HOST
    port = settings.HOLE_PORT
    try:
        use_ssl = settings.MASTER_USES_SSL
    except AttributeError:
        use_ssl = False

    try:
        validate_cert = settings.VALIDATE_CERT_MASTER
    except AttributeError:
        validate_cert = False

    return {'host': host, 'port': port,
            'use_ssl': use_ssl,
            'validate_cert': validate_cert}


async def get_builders_for_buildsets(user, buildsets):
    """Returns a list of builders used in given buildsets

    :param user: The user to authenticate in the master
    :param buildsets: A list of buildsets returned by the master."""

    from toxicbuild.ui.models import Builder

    builders = set()
    buildsets = buildsets or []
    for buildset in buildsets:
        for build in buildset.builds:
            builders.add(build.builder)

    # Now the thing here is: the builders here are made
    # from the response of buildset-list. It returns only
    # the builder id for builds, so now I retrieve the
    # 'full' builder using builder-list
    ids = [b.id for b in builders]
    builders = await Builder.list(user, id__in=ids)
    builders_dict = {str(b.id): b for b in builders}
    for buildset in buildsets:
        for build in buildset.builds:
            build.builder = builders_dict[build.builder.id]

    return sorted(builders, key=lambda b: b.name)


def get_defaulte_locale_morsel():
    """Returns a :class:`~http.cookies.Morsel` instance with
    `en_US` as its value.
    """

    locale_str = 'en_US'
    m = Morsel()
    m.set('locale', locale_str, locale_str)
    return m
