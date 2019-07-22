# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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

from http.cookies import Morsel

from toxicbuild.core.utils import DTFORMAT
from toxicbuild.ui import settings


def get_dtformat():
    try:
        dtformat = settings.DTFORMAT
    except AttributeError:
        dtformat = DTFORMAT

    return dtformat


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


def get_default_timezone_morsel():
    """Returns a :class:`~http.cookies.Morsel` instance with
    `UTC` as its value.
    """

    tzname = 'UTC'
    m = Morsel()
    m.set('locale', tzname, tzname)
    return m
