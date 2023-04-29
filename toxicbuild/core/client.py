# -*- coding: utf-8 -*-

# Copyright 2015, 2017-2018 Juca Crispim <juca@poraodojuca.net>

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
from collections import OrderedDict
import json
import ssl
import traceback
from toxicbuild.core import utils
from toxicbuild.core.exceptions import ToxicClientException, BadJsonData


__doc__ = """This module implements a base client for basic
tcp communication, reading and writing json data.

Usage:
``````

.. code-block:: python

    host = 'somehost.net'
    port = 1234
    async with BaseToxicClient(host, port):
        await client.write({'hello': 'world'})
        json_response = await client.get_response()

"""


class BaseToxicClient(utils.LoggerMixin):

    """ Base client for communication with toxicbuild servers. """

    def __init__(self, host, port, use_ssl=False,
                 validate_cert=True, **ssl_kw):
        """:para host: The host to connect
        :param port: The port that the server is listening.
        :param use_ssl: Indicates if we should use a secure connection.
        :param validate_cert: Indicates if we should validate the ssl cert
          used by the server.
        :param ssl_kw: Named arguments to ``ssl.create_default_context()``
        """
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.validate_cert = validate_cert
        self.ssl_kw = ssl_kw
        self.reader = None
        self.writer = None
        self._connected = False

    def is_connected(self):
        return self._connected

    def __enter__(self):
        if not self.is_connected():
            msg = "Use ``async with``"
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

            This is called by the asynchronous context manager
            (aka ``async with``)
        """

        if self.use_ssl:
            ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH,
                                                     **self.ssl_kw)
            if not self.validate_cert:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            kw = {'ssl': ssl_context}
        else:
            kw = {}

        self.reader, self.writer = await asyncio.open_connection(
            self.host, self.port, **kw)
        self._connected = True

    def disconnect(self):
        """Disconnects from the server"""
        self.log('disconecting...', level='debug')
        self.writer.close()
        self._connected = False

    async def write(self, data, timeout=None):
        """ Writes ``data`` to the server.

        :param data: Data to be sent to the server. Will be converted to
          json and enconded using utf-8.
        :param timeout: Timeout for the write operation. If None there is
          no timeout.
        """
        data = json.dumps(data)
        await utils.write_stream(self.writer, data, timeout=timeout)

    async def read(self, timeout=None):
        """Reads data from the server. Expects a json.
        param timeout: Timeout for the read operation. If None there is
          no timeout
        """
        # '{}' is decoded as an empty dict, so in json
        # context we can consider it as being a False json
        data = await utils.read_stream(self.reader, timeout=timeout)
        data = data.decode() or '{}'
        try:
            json_data = json.loads(data, object_pairs_hook=OrderedDict)
        except Exception:
            msg = traceback.format_exc()
            self.log(msg, level='error')
            raise BadJsonData(data)

        return json_data

    async def get_response(self, timeout=None):
        """Reads data from the server and raises and exception in case of
        error"""
        response = await self.read(timeout=timeout)

        if 'code' in response and int(response['code']) != 0:
            raise ToxicClientException(response['body']['error'])
        return response

    async def request2server(self, action, body, token, timeout=None):
        """Performs a request to a toxicbuild server and
        server returns the response.

        :param action: The action to perform on the server.
        :param body: The body for the action.
        :param token: An authentication token.
        """
        data = {'action': action, 'body': body,
                'token': token}
        await self.write(data)
        response = await self.get_response(timeout=timeout)
        return response['body'][action]
