# -*- coding: utf-8 -*-

# Copyright 2015-2017 Juca Crispim <juca@poraodojuca.net>

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

import asyncio
from toxicbuild.core import BaseToxicClient
from toxicbuild.core.exceptions import ToxicClientException
from toxicbuild.ui import settings
from toxicbuild.ui.exceptions import (UserDoesNotExist, NotEnoughPerms,
                                      BadResetPasswordToken)


class UIHoleClient(BaseToxicClient):
    """Client for the master's hole. """

    def __init__(self, requester, *args, hole_token=None, **kwargs):
        """:param requester: The users who is willing to talk to the
        master.
        :param args: List arguments passed to super() constructor.
        :param hole_token: The token for access on the master.
        :param kwargs: Named arguments passed to super() constructor."""

        self.hole_token = hole_token or settings.HOLE_TOKEN
        self.requester = requester
        super().__init__(*args, **kwargs)

    def __getattr__(self, name):
        action = name.replace('_', '-')

        @asyncio.coroutine
        def _2serverandback(**kwargs):
            return (yield from self.request2server(action, body=kwargs))

        return _2serverandback

    @asyncio.coroutine
    def request2server(self, action, body):
        """Performs a request to a hole server.

        :param action: The action to perform on the server.
        :param body: The body of the request, with the actions parameters.
        """

        data = {'action': action, 'body': body,
                'token': self.hole_token}

        if action not in ['user-authenticate']:
            data['user_id'] = str(self.requester.id)

        yield from self.write(data)
        response = yield from self.get_response()
        return response['body'][action]

    @asyncio.coroutine
    def connect2stream(self, body):
        """Connects the client to the master's hole stream."""

        action = 'stream'
        user_body = {'user_id': str(self.requester.id)}
        body.update(user_body)

        yield from self.request2server(action, body)

    @asyncio.coroutine
    def get_response(self):
        response = yield from self.read()

        if 'code' in response and int(response['code']) == 1:
            # server error
            raise ToxicClientException(response['body']['error'])

        if 'code' in response and int(response['code']) == 2:
            raise UserDoesNotExist(response['body']['error'])

        if 'code' in response and int(response['code']) == 3:
            raise NotEnoughPerms(response['body']['error'])

        if 'code' in response and int(response['code']) == 4:
            raise BadResetPasswordToken(response['body']['error'])

        return response


@asyncio.coroutine
def get_hole_client(requester, host, port, hole_token=None,
                    **kwargs):
    client = UIHoleClient(requester, host, port, hole_token=hole_token,
                          **kwargs)
    yield from client.connect()
    return client
