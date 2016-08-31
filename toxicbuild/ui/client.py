# -*- coding: utf-8 -*-

# Copyright 2015 2016 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from toxicbuild.core import BaseToxicClient
from toxicbuild.ui import settings


class UIHoleClient(BaseToxicClient):

    def __getattr__(self, name):
        action = name.replace('_', '-')

        @asyncio.coroutine
        def _2serverandback(**kwargs):
            return (yield from self.request2server(action, body=kwargs))

        return _2serverandback

    @asyncio.coroutine
    def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'token': settings.HOLE_TOKEN}

        yield from self.write(data)
        response = yield from self.get_response()
        return response['body'][action]

    @asyncio.coroutine
    def connect2stream(self):
        """Connects the client to the master's hole stream."""

        action = 'stream'
        body = {}

        yield from self.request2server(action, body)


@asyncio.coroutine
def get_hole_client(host, port):
    client = UIHoleClient(host, port)
    yield from client.connect()
    return client
