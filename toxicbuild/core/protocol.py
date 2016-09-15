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
try:
    from asyncio import ensure_future
except ImportError:  # pragma: no cover
    from asyncio import async as ensure_future
import json
import time
import traceback
from toxicbuild.core import utils


class BaseToxicProtocol(asyncio.StreamReaderProtocol, utils.LoggerMixin):

    """ Base protocol for toxicbulid servers
    """

    # Salt used to encrypt incomming token.
    salt = None
    # This is the token used to authenticate incomming requests.
    encrypted_token = None

    def __init__(self, loop, connection_lost_cb=None):
        """:param loop: An asyncio loop.
        :param connection_lost_cb: Callable to be executed when connection
          is closed. Gets an exception or None as parameter."""

        self.raw_data = None
        self.json_data = None
        self.action = None
        self._connected = False
        # make tests easier
        self._check_data_future = None
        self._client_connected_future = None
        self.connection_lost_cb = connection_lost_cb

        reader = asyncio.StreamReader(loop=loop)
        super().__init__(reader, loop=loop)

    def __call__(self):
        return self

    def connection_made(self, transport):
        """ Called once, when the client connects.

        :param transport: transport for asyncio.StreamReader and
          asyncio.StreamWriter.
        """
        self._transport = transport
        self._stream_reader.set_transport(transport)
        self._stream_writer = asyncio.StreamWriter(transport, self,
                                                   self._stream_reader,
                                                   self._loop)
        self._connected = True

        self.peername = self._transport.get_extra_info('peername')
        self._check_data_future = ensure_future(self.check_data())
        self._check_data_future.add_done_callback(self._check_data_cb)

    def connection_lost(self, exc):
        self.close_connection()
        if self.connection_lost_cb:
            self.connection_lost_cb(exc)

    @asyncio.coroutine
    def check_data(self):
        """ Checks if the data is valid, it means, checks if has some data,
        checks if it is a valid json and checks if it has a ``action`` key
        """

        self.data = yield from self.get_json_data()

        if not self.data:
            msg = 'Something wrong with your data {!r}'.format(self.raw_data)
            yield from self.send_response(code=1, body={'error': msg})
            return self.close_connection()

        token = self.data.get('token')
        if not token:
            msg = 'No auth token'
            yield from self.send_response(code=2, body={'error': msg})
            return self.close_connection()

        incomming_token = utils.bcrypt_string(token, self.salt)
        if incomming_token != self.encrypted_token:
            msg = 'Bad auth token'
            yield from self.send_response(code=3, body={'error': msg})
            return self.close_connection()

        self.action = self.data.get('action')

        if not self.action:
            msg = 'No action found!'
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
        data = json.dumps(response)
        yield from utils.write_stream(self._stream_writer, data)

    @asyncio.coroutine
    def get_raw_data(self):
        """ Returns the raw data sent by the client
        """
        return utils.read_stream(self._stream_reader)

    @asyncio.coroutine
    def get_json_data(self):
        """Returns the json sent by the client."""

        data = (yield from self.get_raw_data()).decode()

        try:
            data = json.loads(data)
        except Exception:
            msg = '{}\n{}'.format(traceback.format_exc(), data)
            self.log(msg, level='error')
            data = None

        return data

    def _check_data_cb(self, future):
        # The thing here is: run client_connected only if everything ok
        # on check_data
        if not self._connected:  # pragma no cover
            return

        # wrapping it to log it.
        @asyncio.coroutine
        def logged_cb():
            init = (time.time() * 1e3)
            status = yield from self.client_connected()
            end = (time.time() * 1e3)
            self.log('{}: {} {}'.format(self.action, status, (end - init)))

        self._client_connected_future = logged_cb()
        self._client_connected_future = ensure_future(
            self._client_connected_future)
