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

from asyncio import ensure_future, gather
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master.repository import Repository
from toxicbuild.output.exchanges import (repo_notifications,
                                         build_notifications)


class OutputMethodServer(LoggerMixin):
    """Fetchs messages from notification queues and dispatches the
    needed output methods."""

    async def run(self):
        fs = [self._handle_build_notifications(),
              self._handle_repo_notifications()]

        await gather(*fs)

    async def _handle_build_notifications(self):
        t = ensure_future(self._handle_notifications(build_notifications))
        return t

    async def _handle_repo_notifications(self):
        t = ensure_future(self._handle_notifications(repo_notifications))
        return t

    async def _handle_notifications(self, exchange):
        async with await exchange.consume() as consumer:
            async for msg in consumer:
                self.log('Got msg {}'.format(msg.body), level='debug')
                ensure_future(self.run_plugins(msg.body))
                await msg.acknowledge()

    async def run_plugins(self, msg):
        """Runs all plugins for a given repository that react to a given
        event type.

        :param msg: The incomming message from a notification"""

        repo = await Repository.get(id=msg['repository_id'])
        for plugin in repo.get_plugins_for_event(msg['event_type']):
            ensure_future(plugin.run(repo, msg))
