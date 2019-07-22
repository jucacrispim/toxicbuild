# -*- coding: utf-8 -*-

# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

from toxicbuild.core.exchange import Exchange

# pylint: disable=global-statement

gconn = None


def create_exchanges(conn):
    global gconn

    gconn = conn

    repo_status_changed = Exchange('toxicbuild.repo_status_changed',
                                   connection=conn,
                                   bind_publisher=False,
                                   exclusive_consumer_queue=True,
                                   exchange_type='direct')

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

    repo_notifications = Exchange('toxicbuild.repo_notifications',
                                  connection=conn,
                                  bind_publisher=True,
                                  exclusive_consumer_queue=False,
                                  exchange_type='direct')

    build_notifications = Exchange('toxicbuild.build_notifications',
                                   connection=conn,
                                   bind_publisher=True,
                                   exclusive_consumer_queue=False,
                                   exchange_type='direct')

    return {'repo_status_changed': repo_status_changed,
            'repo_added': repo_added,
            'ui_notifications': ui_notifications,
            'repo_notifications': repo_notifications,
            'build_notifications': build_notifications}


async def disconnect_exchanges():  # pragma no cover
    await gconn.connection.disconnect()
