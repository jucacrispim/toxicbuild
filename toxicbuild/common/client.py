# -*- coding: utf-8 -*-

# Copyright 2015-2017, 2019 Juca Crispim <juca@poraodojuca.net>

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

from toxicbuild.core import BaseToxicClient
from toxicbuild.core.exceptions import ToxicClientException
from toxicbuild.core.utils import LoggerMixin
from .exceptions import (UserDoesNotExist, NotEnoughPerms,
                         BadResetPasswordToken, AlreadyExists)


class HoleClient(BaseToxicClient, LoggerMixin):
    """Client for the master's hole. """

    settings = None

    def __init__(self, requester, *args, hole_token=None, **kwargs):
        """:param requester: The user who is willing to talk to the
        master.
        :param args: List arguments passed to super() constructor.
        :param hole_token: The token for access on the master.
        :param kwargs: Named arguments passed to super() constructor."""

        self.hole_token = hole_token or self.settings.HOLE_TOKEN
        self.requester = requester
        super().__init__(*args, **kwargs)

    def __getattr__(self, name):
        action = name.replace('_', '-')

        async def _2serverandback(**kwargs):
            r = await self.request2server(action, body=kwargs)
            return r

        return _2serverandback

    async def request2server(self, action, body):
        """Performs a request to a hole server.

        :param action: The action to perform on the server.
        :param body: The body of the request, with the actions parameters.
        """

        data = {'action': action, 'body': body,
                'token': self.hole_token}

        self.log('requesting action: ' + str(data), level='debug')

        if action not in ['user-authenticate']:
            data['user_id'] = str(self.requester.id)

        await self.write(data)
        response = await self.get_response()
        print(response)
        return response['body'][action]

    async def connect2stream(self, body):
        """Connects the client to the master's hole stream."""

        action = 'stream'
        user_body = {'user_id': str(self.requester.id)}
        body.update(user_body)

        await self.request2server(action, body)

    async def get_response(self):
        response = await self.read()

        if 'code' in response and int(response['code']) == 1:
            # server error
            raise ToxicClientException(response['body']['error'])

        if 'code' in response and int(response['code']) == 2:
            raise UserDoesNotExist(response['body']['error'])

        if 'code' in response and int(response['code']) == 3:
            raise NotEnoughPerms(response['body']['error'])

        if 'code' in response and int(response['code']) == 4:
            raise BadResetPasswordToken(response['body']['error'])

        if 'code' in response and int(response['code']) == 5:
            raise AlreadyExists(response['body']['error'])

        return response


async def get_hole_client(requester, host, port, hole_token=None,
                          **kwargs):
    client = HoleClient(requester, host, port, hole_token=hole_token,
                        **kwargs)
    await client.connect()
    return client
