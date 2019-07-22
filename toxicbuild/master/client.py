# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

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
from asyncio import ensure_future
from toxicbuild.core import BaseToxicClient
from toxicbuild.core.exceptions import ToxicClientException
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master.utils import (get_build_config_type,
                                     get_build_config_filename)


class BuildClient(BaseToxicClient, LoggerMixin):

    """ A client to :class:`toxicbuild.slave.server.BuildServer`
    """

    def __init__(self, slave, *args, **kwargs):
        self.slave = slave
        super().__init__(*args, **kwargs)
        self.config_type = get_build_config_type()
        self.config_filename = get_build_config_filename()

    async def healthcheck(self):
        """ Asks to know if the server is up and running
        """
        data = {'action': 'healthcheck'}
        try:
            await self.write(data)
            response = await self.get_response()
            r = True
        except Exception:
            response = None
            r = False

        # When we try to connect to a secure slave using a non-secure
        # connection we get an empty response
        if response == '':
            raise ToxicClientException(
                'Bad connection. Check the slave ssl settings.')
        return r

    async def list_builders(self, repo_url, vcs_type, branch, named_tree):
        """ Asks the server for the builders available for ``repo_url``,
        on ``branch`` and ``named_tree``.
        """

        data = {'action': 'list_builders',
                'body': {'repo_url': repo_url,
                         'vcs_type': vcs_type,
                         'branch': branch,
                         'named_tree': named_tree,
                         'config_type': self.config_type,
                         'config_filename': self.config_filename}}
        await self.write(data)
        response = await self.get_response()
        builders = response['body']['builders']
        return builders

    async def build(self, build, process_coro=None):
        """Requests a build for the build server.

        :param build: The build that will be executed.
        :param process_coro: A coroutine to process the intermediate
          build information sent by the build server."""

        self.log('Starting build {}'.format(build.uuid), level='debug')

        repository = await build.repository
        builder_name = (await build.builder).name
        slave = await build.slave
        data = {'action': 'build',
                'token': slave.token,
                'body': {'repo_url': repository.get_url(),
                         'vcs_type': repository.vcs_type,
                         'branch': build.branch,
                         'named_tree': build.named_tree,
                         'builder_name': builder_name,
                         'config_type': self.config_type,
                         'config_filename': self.config_filename,
                         'builders_from': build.builders_from}}
        if build.external:
            data['body']['external'] = build.external.to_dict()

        await self.write(data)
        futures = []
        build_info = None
        while True:
            r = await self.get_response()

            if not r:
                break

            build_info = r['body']
            if build_info is None:
                return
            if process_coro:
                future = ensure_future(process_coro(
                    build, repository, build_info))
                futures.append(future)

        if futures:
            await asyncio.gather(*futures)
        return build_info


async def get_build_client(slave, addr, port, use_ssl=True,
                           validate_cert=True):
    """ Instanciate :class:`toxicbuild.master.client.BuildClient` and
    connects it to a build server
    """

    client = BuildClient(slave, addr, port, use_ssl=use_ssl,
                         validate_cert=validate_cert)
    await client.connect()
    return client
