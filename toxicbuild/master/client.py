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

from asyncio import ensure_future
from toxicbuild.core import BaseToxicClient


class BuildClient(BaseToxicClient):

    """ A client to :class:`toxicbuild.slave.server.BuildServer`
    """

    def __init__(self, slave, *args, **kwargs):
        self.slave = slave
        super().__init__(*args, **kwargs)

    async def healthcheck(self):
        """ Asks to know if the server is up and running
        """
        data = {'action': 'healthcheck'}
        try:
            await self.write(data)
            response = await self.get_response()
            del response
            return True
        except Exception:
            return False

    async def list_builders(self, repo_url, vcs_type, branch, named_tree):
        """ Asks the server for the builders available for ``repo_url``,
        on ``branch`` and ``named_tree``.
        """

        data = {'action': 'list_builders',
                'body': {'repo_url': repo_url,
                         'vcs_type': vcs_type,
                         'branch': branch,
                         'named_tree': named_tree}}
        await self.write(data)
        response = await self.get_response()
        builders = response['body']['builders']
        return builders

    async def build(self, build, process_coro=None):
        """Requests a build for the build server.

        :param build: The build that will be executed.
        :param process_coro: A coroutine to process the intermediate
          build information sent by the build server."""

        repository = await build.repository
        builder_name = (await build.builder).name
        slave = await build.slave
        data = {'action': 'build',
                'token': slave.token,
                'body': {'repo_url': repository.url,
                         'vcs_type': repository.vcs_type,
                         'branch': build.branch,
                         'named_tree': build.named_tree,
                         'builder_name': builder_name}}

        await self.write(data)
        futures = []
        while True:
            r = await self.get_response()

            if not r:
                break

            build_info = r['body']
            if process_coro:
                future = ensure_future(process_coro(build, build_info))
                futures.append(future)

        return futures


async def get_build_client(slave, addr, port):
    """ Instanciate :class:`toxicbuild.master.client.BuildClient` and
    connects it to a build server
    """

    client = BuildClient(slave, addr, port)
    await client.connect()
    return client
