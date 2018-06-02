# -*- coding: utf-8 -*-

# Copyright 2015, 2017 Juca Crispim <juca@poraodojuca.net>

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
from collections import OrderedDict
import json
import traceback
from toxicbuild.core import utils
from toxicbuild.core.exceptions import ToxicClientException, BadJsonData


__doc__ = """This module implements a base client for basic
comunication tcp communication, reading and writing json data.

Usage:
``````

.. code-block:: python

    host = 'somehost.net'
    port = 1234
    async with BaseToxicClient(host, port):
        await client.write({'hello': 'world'})
        response = await client.get_response()

"""


class BaseToxicClient(utils.LoggerMixin):

    """ Base client for communication with toxicbuild servers. """

    def __init__(self, host, port, loop=None):
        self.host = host
        self.port = port
        self.loop = loop or asyncio.get_event_loop()
        self.reader = None
        self.writer = None
        self._connected = False

    def __enter__(self):
        if not self._connected:
            msg = 'You must connect with "yield from client.connect()" '
            msg += 'before you can __enter__ on it. Sorry.'
            raise ToxicClientException(msg)
        return self

    async def __aenter__(self):
        await self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.__exit__(exc_type, exc_val, exc_tb)

    async def connect(self):
        """Connects to the server.

        .. note::

            This is called the the asynchronous context manager
            (aka ``async with``)"""

        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port, loop=self.loop)
        self._connected = True

    def disconnect(self):
        """Disconnects from the server"""
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
        """Reads data from the server. Expects a json."""
        # '{}' is decoded as an empty dict, so in json
        # context we can consider it as being a False json
        data = yield from utils.read_stream(self.reader)
        data = data.decode() or '{}'

        try:
            json_data = json.loads(data, object_pairs_hook=OrderedDict)
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level='error')
            raise BadJsonData(data)

        return json_data

    @asyncio.coroutine
    def get_response(self):
        """Reads data from the server and raises and exception in case of
        error"""
        response = yield from self.read()

        if 'code' in response and int(response['code']) != 0:
            raise ToxicClientException(response['body']['error'])
        return response
