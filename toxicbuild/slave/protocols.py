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
from toxicbuild.slave import BuildManager
from toxicbuild.slave.exceptions import BadData


class BuildServerProtocol(asyncio.StreamReaderProtocol):
    """ A simple server for build requests.
    """

    def __init__(self, loop):
        self.raw_data = None
        self.data = None
        reader = asyncio.StreamReader(loop=loop)
        super().__init__(reader, loop=loop)

    def __call__(self):
        return self

    def connection_made(self, transport):
        self._transport = transport
        self._stream_reader.set_transport(transport)
        self._stream_writer = asyncio.StreamWriter(transport, self,
                                                   self._stream_reader,
                                                   self._loop)

        res = self.client_connected()
        self._loop.create_task(res)

    @asyncio.coroutine
    def client_connected(self):
        self.raw_data = yield from self.get_raw_data()
        self.data = self.get_json_data()
        if not self.data:
            msg = 'Something wrong with your data {!r}'.format(self.raw_data)
            yield from self.send_response(code=1, body=msg)
            return self.close_connection()

        action = self.data.get('action')
        if not action:
            msg = 'No action found!'
            yield from self.send_response(code=1, body=msg)
            return self.close_connection()

        try:
            if action == 'healthcheck':
                yield from self.healthcheck()

            elif action == 'list_builders':
                yield from self.list_builders()

            elif action == 'build':
                # build has a strange behavior. It sends messages to the client
                # directly. I think it should be an iterable here and the
                # protocol should send the messages. But how do to that?
                # I tought, instead of the iterable, use messages sent from
                # BuildManager and captured by the protocol, but didn't try
                # that yet. Any ideas?
                build_info = yield from self.build()
                yield from self.send_response(code=0, body=build_info)
        except BadData:
            msg = 'Something wrong with your data {!r}'.format(self.raw_data)
            yield from self.send_response(code=1, body=msg)

        self.close_connection()

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
    def healthcheck(self):
        """ Informs that the server is up and running
        """
        yield from self.send_response(code=0, body='I\'m alive!')

    @asyncio.coroutine
    def list_builders(self):
        """ Informs all builders' names for this repo/branch/named_tree
        """
        manager = yield from self.get_buildmanager()
        builder_names = manager.list_builders()
        yield from self.send_response(code=0, body={'builders': builder_names})

    @asyncio.coroutine
    def build(self):
        """ Performs a build requested by the client using the params sent
        in the request data
        """
        manager = yield from self.get_buildmanager()
        try:
            builder_name = self.data['body']['builder_name']
        except KeyError:  # pragma: no cover
            raise BadData

        builder = manager.load_builder(builder_name)
        build_info = yield from builder.build()

    def close_connection(self):
        """ Closes the connection with the client
        """
        self._stream_writer.close()

    @asyncio.coroutine
    def get_buildmanager(self):
        """ Returns the builder manager for this request
        """
        try:
            repo_url = self.data['body']['repo_url']
            branch = self.data['body']['branch']
            vcs_type = self.data['body']['vcs_type']
            named_tree = self.data['body']['named_tree']
        except KeyError:
            raise BadData('Bad data!')

        manager = BuildManager(self, repo_url, vcs_type, branch, named_tree)
        yield from manager.update_and_checkout()
        return manager

    @asyncio.coroutine
    def get_raw_data(self):
        """ Returns the raw data sent by the client
        """
        data = yield from self._stream_reader.read(self._stream_reader._limit)
        return data

    def get_json_data(self):
        """Returns the json sent by the client."""

        data = self.raw_data.decode()

        try:
            data = json.loads(data)
        except Exception:  # pragma: no cover
            data = None

        return data
