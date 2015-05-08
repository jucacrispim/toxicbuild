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
from toxicbuild.core.protocol import BaseToxicProtocol
from toxicbuild.slave import BuildManager
from toxicbuild.slave.exceptions import BadData


class BuildServerProtocol(BaseToxicProtocol):

    """ A simple server for build requests.
    """

    @asyncio.coroutine
    def client_connected(self):
        try:
            if self.action == 'healthcheck':
                self.log('executing {}'.format(self.action))
                yield from self.healthcheck()

            elif self.action == 'list_builders':
                self.log('executing {}'.format(self.action))
                yield from self.list_builders()

            elif self.action == 'build':
                self.log('executing {}'.format(self.action))
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
            self.log('bad data')
            yield from self.send_response(code=1, body=msg)
        except Exception as e:
            self.log(e.args[0])
            yield from self.send_response(code=1, body=e.args[0])

        self.close_connection()

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
        return build_info

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
