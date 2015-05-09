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
from toxicbuild.core import BaseToxicClient


class BuildClient(BaseToxicClient):

    """ A client to :class:`toxicbuild.slave.server.BuildServer`
    """

    @asyncio.coroutine
    def healthcheck(self):
        """ Asks to know if the server is up and running
        """
        data = {'action': 'healthcheck'}
        try:
            self.write(data)
            response = yield from self.get_response()
            del response
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
