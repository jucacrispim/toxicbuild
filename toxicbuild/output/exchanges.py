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

from toxicbuild.core.exchange import AmqpConnection
from toxicbuild.core.exchanges import create_exchanges
from toxicbuild.output import settings

conn_kw = settings.RABBITMQ_CONNECTION

conn = AmqpConnection(**conn_kw)
core_exchanges = create_exchanges(conn)  # pylint: disable-all
repo_status_changed = core_exchanges['repo_status_changed']
repo_added = core_exchanges['repo_added']
ui_notifications = core_exchanges['ui_notifications']
repo_notifications = core_exchanges['repo_notifications']
build_notifications = core_exchanges['build_notifications']


async def connect_exchanges():

    await conn.connect()

    await repo_notifications.declare()
    await build_notifications.declare()
    await repo_status_changed.declare()
    await repo_added.declare()
    await ui_notifications.declare()


async def disconnect_exchanges():
    await conn.disconnect()
