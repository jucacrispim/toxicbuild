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
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from .exchange import AmqpConnection, Exchange


conn = AmqpConnection()

notifications = Exchange('toxicbuild.notifications',
                         connection=conn,
                         bind_publisher=True,
                         exclusive_consumer_queue=False,
                         exchange_type='direct')

integrations_notifications = Exchange('toxicbuild.integrations-notifications',
                                      connection=conn,
                                      bind_publisher=True,
                                      exclusive_consumer_queue=False,
                                      exchange_type='direct')

ui_notifications = Exchange('toxicbuild.ui-notifications',
                            connection=conn,
                            bind_publisher=False,
                            exclusive_consumer_queue=True,
                            exchange_type='direct')

update_code = Exchange('toxicbuild.update_code',
                       connection=conn,
                       exchange_type='direct',
                       durable=True,
                       bind_publisher=True)


poll_status = Exchange('toxicbuild.poll_status',
                       connection=conn,
                       exchange_type='direct',
                       bind_publisher=False,
                       exclusive_consumer_queue=True)


revisions_added = Exchange('toxicbuild.revisions_added',
                           connection=conn,
                           bind_publisher=True,
                           durable=True,
                           exchange_type='direct')


scheduler_action = Exchange('toxicbuild.scheduler_action',
                            connection=conn,
                            bind_publisher=True,
                            durable=True,
                            exchange_type='direct')


async def declare():
    await notifications.declare()
    await integrations_notifications.declare()
    await ui_notifications.declare()
    await update_code.declare()
    await poll_status.declare()
    await revisions_added.declare()
    await scheduler_action.declare()
