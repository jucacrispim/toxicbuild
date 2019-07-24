# -*- coding: utf-8 -*-

# Copyright 2015-2018 Juca Crispim <juca@poraodojuca.net>

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

import traceback
from toxicbuild.core.protocol import BaseToxicProtocol
from toxicbuild.core.utils import log, datetime2string, now
from toxicbuild.slave import settings
from toxicbuild.slave.managers import BuildManager
from toxicbuild.slave.exceptions import (BadData, BadBuilderConfig)


class BuildServerProtocol(BaseToxicProtocol):

    """ A simple server for build requests.
    """
    encrypted_token = settings.ACCESS_TOKEN
    _clients_connected = 0
    _is_shuting_down = False

    async def client_connected(self):
        if type(self)._is_shuting_down:
            self.log('Rejecting connection. Shutting down',
                     level='warning')
            self.close_connection()
            return None

        type(self)._clients_connected += 1
        try:
            self.log('executing {} for {}'.format(self.action, self.peername))
            status = 0
            if self.action == 'healthcheck':
                await self.healthcheck()

            elif self.action == 'list_builders':
                await self.list_builders()

            elif self.action == 'build':
                # build has a strange behavior. It sends messages to the client
                # directly. I think it should be an iterable here and the
                # protocol should send the messages. But how do to that?
                # I tought, instead of the iterable, use messages sent from
                # BuildManager and captured by the protocol, but didn't try
                # that yet. Any ideas?

                build_info = await self.build()

                await self.send_response(code=0, body=build_info)
            else:
                msg = 'Action {} does not exist'.format(self.action)
                self.log(msg, level='error')
                await self.send_response(code=1, body={'error': msg})

        except BadData:
            msg = 'Something wrong with your data {}'.format(self.raw_data)
            self.log('bad data', level='error')
            await self.send_response(code=1, body={'error': msg})
            status = 1
        except Exception as e:
            self.log(e.args[0], level='error')
            msg = traceback.format_exc()
            status = 1
            await self.send_response(code=1, body={'error': msg})

        finally:
            self.close_connection()
            type(self)._clients_connected -= 1

        return status

    async def healthcheck(self):
        """ Informs that the server is up and running
        """
        code = 0
        body = "I'm alive!"

        await self.send_response(code=code, body=body)

    async def list_builders(self):
        """ Informs all builders' names for this repo/branch/named_tree
        """
        manager = await self.get_buildmanager()
        with manager:
            # We do not work after wait because if we wait for it
            # the other instance working is in the same named_tree
            await manager.update_and_checkout(work_after_wait=False)

            builder_names = manager.list_builders()
        await self.send_response(code=0, body={'builders': builder_names})

    async def build(self):
        """ Performs a build requested by the client using the params sent
        in the request data
        """

        manager = await self.get_buildmanager()
        with manager:
            external = self.data['body'].get('external')
            await manager.update_and_checkout(work_after_wait=False,
                                              external=external)

            try:
                builder_name = self.data['body']['builder_name']
            except KeyError:
                raise BadData("No builder name for build.")

            try:
                builder = await manager.load_builder(builder_name)
            except BadBuilderConfig:
                build_info = {'steps': [], 'status': 'exception',
                              'started': datetime2string(now()),
                              'finished': datetime2string(now()),
                              'branch': manager.branch,
                              'named_tree': manager.named_tree}
            else:
                build_info = await builder.build()
            return build_info

    async def get_buildmanager(self):
        """ Returns the builder manager for this request
        """
        try:
            repo_url = self.data['body']['repo_url']
            branch = self.data['body']['branch']
            vcs_type = self.data['body']['vcs_type']
            named_tree = self.data['body']['named_tree']
        except KeyError as e:
            raise BadData('Bad data! Missing {}'.format(str(e)))

        config_type = self.data['body'].get('config_type') or 'yml'
        config_filename = self.data['body'].get(
            'config_filename') or 'toxicbuild.yml'
        builders_from = self.data['body'].get('builders_from')

        manager = BuildManager(self, repo_url, vcs_type, branch, named_tree,
                               config_type=config_type,
                               config_filename=config_filename,
                               builders_from=builders_from)

        return manager

    def log(self, msg, level='info'):
        log('[{}] {} '.format(type(self).__name__, msg), level)
