# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
import json
import traceback
from toxicbuild.core import utils
from toxicbuild.core.exceptions import ToxicClientException, BadJsonData


class BaseToxicClient(utils.LoggerMixin):

    """ Base client for access toxicbuild servers. """

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.loop = asyncio.get_event_loop()
        self.reader = None
        self.writer = None
        self._connected = False

    def __enter__(self):
        if not self._connected:
            msg = 'You must connect with "yield from client.connect()" '
            msg += 'before you can __enter__ on it. Sorry.'
            raise ToxicClientException(msg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @asyncio.coroutine
    def connect(self):
        self.reader, self.writer = yield from asyncio.open_connection(
            self.host, self.port, loop=self.loop)
        self._connected = True

    def disconnect(self):
        self.log('disconecting...', level='debug')
        self.writer.close()
        self._connected = False

    @asyncio.coroutine
    def write(self, data):
        """ Writes ``data`` to the server.

        :param data: Data to be sent to the server. Will be converted to
          json and enconded using utf-8.
        """
        data = json.dumps(data)
        yield from utils.write_stream(self.writer, data)

    @asyncio.coroutine
    def read(self):
        # '{}' is decoded as an empty dict, so in json
        # context we can consider it as being a False json
        data = yield from utils.read_stream(self.reader)
        data = data.decode() or '{}'
        try:
            json_data = json.loads(data)
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level='error')
            raise BadJsonData(data)

        return json_data

    @asyncio.coroutine
    def get_response(self):
        response = yield from self.read()

        if 'code' in response and int(response['code']) != 0:
            raise ToxicClientException(response['body']['error'])
        return response
