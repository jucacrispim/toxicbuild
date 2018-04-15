# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

from toxicbuild.core.exchange import Exchange


repo_status_changed = None
repo_added = None


def create_exchanges(conn):
    global repo_status_changed
    global repo_added

    if not repo_status_changed:  # pragma no branch
        repo_status_changed = Exchange('toxicbuild.repo_status_changed',
                                       connection=conn,
                                       bind_publisher=False,
                                       exclusive_consumer_queue=True,
                                       exchange_type='direct')

    if not repo_added:  # pragma no branch
        repo_added = Exchange('toxicbuild.repo_added',
                              connection=conn,
                              bind_publisher=False,
                              exclusive_consumer_queue=True,
                              exchange_type='direct')

    ui_notifications = Exchange('toxicbuild.ui_notifications',
                                connection=conn,
                                bind_publisher=False,
                                exclusive_consumer_queue=True,
                                exchange_type='direct')

    return {'repo_status_changed': repo_status_changed,
            'repo_added': repo_added,
            'ui_notifications': ui_notifications}


async def disconnect_exchanges():  # pragma no cover
    await repo_status_changed.connection.disconnect()
