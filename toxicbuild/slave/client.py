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

import traceback
from toxicbuild.core.client import BaseToxicClient
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.slave import settings
from toxicbuild.slave.exceptions import NotConnected


class ContainerBuildClient(LoggerMixin):
    """Client to request builds to the build containers."""

    def __init__(self, build_data, container):
        """:param build_data: Data from the build request that will
        be sent to the slave in a container.
        :param container: A instance of a container that executes builds."""
        self.build_data = build_data
        self.container = container
        self.client = None

    async def __aenter__(self):
        ip = await self.container.get_container_ip()
        port = settings.CONTAINER_SLAVE_PORT

        self.client = BaseToxicClient(ip, port)
        await self.client.__aenter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.__aexit__(exc_type, exc_val, exc_tb)
        self.client = None

    async def build(self, outfn):
        """Request a build to a slave in a container

        :param outfn: A callable that sends the build information back to
          the original requester."""

        token = settings. CONTAINER_SLAVE_TOKEN
        self.build_data['token'] = token

        if not self.client:
            raise NotConnected('You must __aenter__ before using it.')

        await self.client.write(self.build_data)

        while True:
            r = await self.client.get_response()

            if not r:
                break

            await outfn(r['code'], r['body'])

    async def healthcheck(self):
        token = settings. CONTAINER_SLAVE_TOKEN

        if not self.client:
            raise NotConnected('You must __aenter__ before using it.')

        data = {'action': 'healthcheck',
                'token': token,
                'body': {}}

        await self.client.write(data)

        try:
            r = await self.client.get_response()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level='debug')
            ok = False
        else:
            ok = int(r['code']) == 0
        return ok
