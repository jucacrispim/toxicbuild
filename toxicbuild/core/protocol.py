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
import sys
from toxicbuild.core import utils


class BaseToxicProtocol(asyncio.StreamReaderProtocol):

    """ Base protocol for toxicbulid servers
    """

    def __init__(self, loop):
        self.raw_data = None
        self.json_data = None
        self.action = None
        self._connected = False
        # make tests easier
        self._check_data_future = None
        self._client_connected_future = None

        reader = asyncio.StreamReader(loop=loop)
        super().__init__(reader, loop=loop)

    def __call__(self):
        return self

    def connection_made(self, transport):
        """ Called once, when the client connects
        """
        self._transport = transport
        self._stream_reader.set_transport(transport)
        self._stream_writer = asyncio.StreamWriter(transport, self,
                                                   self._stream_reader,
                                                   self._loop)
        self._connected = True

        peername = self._transport.get_extra_info('peername')
        self.log('client connected from {}'.format(peername))

        self._check_data_future = asyncio.async(self.check_data())
        self._check_data_future.add_done_callback(self._check_data_cb)

    @asyncio.coroutine
    def check_data(self):
        """ Checks if the data is valid, it means, checks if has some data,
        checks if it is a valid json and checks if it has a ``action`` key
        """

        self.data = yield from self.get_json_data()

        if not self.data:
            self.log('no data')
            msg = 'Something wrong with your data {!r}'.format(self.raw_data)
            yield from self.send_response(code=1, body=msg)
            return self.close_connection()

        self.action = self.data.get('action')

        if not self.action:
            msg = 'No action found!'
            self.log(msg)
            yield from self.send_response(code=1, body=msg)
            return self.close_connection()

    @asyncio.coroutine
    def client_connected(self):  # pragma no cover
        """ Coroutine that handles connections. You must implement this
        in your sub-classes. When this method is called, ``self.data``,
        containing a dictionary with the data passed in the request and
        ``self.action``, a string indicating which action to take are already
        available.
        """
        raise NotImplementedError

    def close_connection(self):
        """ Closes the connection with the client
        """
        self.log('closing connection')
        self._stream_writer.close()
        self._connected = False

    @asyncio.coroutine
    def send_response(self, code, body):
        """ Send a response to client formated by the (unknown) toxicbuild
        remote build specs.
        :param code: code for this message. code == 0 is success and
          code > 0 is error.
        :param body: response body. It has to be a serializable object.
        """
        response = {'code': code,
                    'body': body}
        data = json.dumps(response).encode('utf-8')
        self._stream_writer.write(data)
        yield from self._stream_writer.drain()

    @asyncio.coroutine
    def get_raw_data(self):
        """ Returns the raw data sent by the client
        """
        data = yield from self._stream_reader.read(self._stream_reader._limit)
        self.raw_data = data
        return self.raw_data

    @asyncio.coroutine
    def get_json_data(self):
        """Returns the json sent by the client."""

        data = (yield from self.get_raw_data()).decode()

        try:
            data = json.loads(data)
        except Exception:  # pragma: no cover
            data = None

        return data

    def log(self, msg, output=sys.stdout):
        utils.log(msg, output)

    def _check_data_cb(self, future):
        # The thing here is: run client_connected only if everything ok
        # on check_data
        if not self._connected:  # pragma no cover
            return

        self._client_connected_future = asyncio.async(self.client_connected())
