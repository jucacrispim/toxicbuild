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
from mongomotor import Document
from mongomotor.fields import StringField, BooleanField
from toxicbuild.core.utils import log
from toxicbuild.master.exceptions import BuildClientException
from toxicbuild.master.signals import (step_started, step_finished,
                                       build_started, build_finished)


class BuildClient:
    """ A client to :class:`toxicbuild.slave.server.BuildServer`
    """

    def __init__(self, addr, port):
        self.addr = addr
        self.port = port
        self.loop = asyncio.get_event_loop()
        self.reader = None
        self.writer = None
        self._connected = False

    def __enter__(self):
        if not self._connected:
            msg = 'You must connect with "yield from client.connect()" '
            msg += 'before you can __enter__ on it. Sorry.'
            raise BuildClientException(msg)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @asyncio.coroutine
    def connect(self):
        self.reader, self.writer = yield from asyncio.open_connection(
            self.addr, self.port, loop=self.loop)
        self._connected = True

    def disconnect(self):
        self.reader.close()
        self.writer.close()
        self._connected = False

    def write(self, data):
        """ Writes ``data`` to the server.

        :param data: Data to be sent to the server. Will be
          converted to json and enconded using utf-8.
        """
        data = json.dumps(data)
        data = data.encode('utf-8')
        self.writer.write(data)

    @asyncio.coroutine
    def read(self):
        # '{}' is decoded as an empty dict, so in json
        # context we can consider it as being a False json
        data = yield from self.reader.read(1000) or '{}'
        data = data.decode()
        return json.loads(data)

    @asyncio.coroutine
    def get_response(self):
        response = yield from self.read()
        if 'code' in response and int(response['code']) != 0:
            raise BuildClientException(response['body'])
        return response

    @asyncio.coroutine
    def healthcheck(self):
        """ Asks to know if the server is up and running
        """
        data = {'action': 'healthcheck'}
        try:
            self.write(data)
            response = yield from self.get_response()
            return True
        except:
            return False

    @asyncio.coroutine
    def list_builders(self, repo_url, vcs_type, branch, named_tree):
        """ Asks the server for the builders available for ``repo_url``,
        on ``branch`` and ``named_tree``.
        """

        data = {'action': 'list_builders',
                'body': {'repo_url': repo_url,
                         'vcs_type': vcs_type,
                         'branch': branch,
                         'named_tree': named_tree}}
        self.write(data)
        response = yield from self.get_response()
        builders = response['body']['builders']
        return builders

    @asyncio.coroutine
    def build(self, repo_url, vcs_type, branch, named_tree, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': repo_url,
                         'vcs_type': vcs_type,
                         'branch': branch,
                         'named_tree': named_tree,
                         'builder_name': builder_name}}
        self.write(data)

        while True:
            r = yield from self.get_response()
            if not r:
                raise StopIteration

            yield r['body']


@asyncio.coroutine
def get_build_client(addr, port):
    """ Instanciate :class:`toxicbuild.master.client.BuildClient` and
    connects it to a build server
    """
    client = BuildClient(addr, port)
    yield from client.connect()
    return client
