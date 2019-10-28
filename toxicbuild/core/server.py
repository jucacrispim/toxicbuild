# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
import signal
import ssl

from .protocol import BaseToxicProtocol
from .utils import LoggerMixin


class ToxicServer(LoggerMixin):

    PROTOCOL_CLS = BaseToxicProtocol

    def __init__(self, addr, port, loop=None, use_ssl=False, **ssl_kw):
        """:param addr: Address from which the server is allowed to receive
        requests. If ``0.0.0.0``, receives requests from all addresses.
        :param port: The port for the slave to listen.
        :param loop: A main loop. If none, ``asyncio.get_event_loop()``
          will be used.
        :param use_ssl: Indicates is the connection uses ssl or not.
        :param ssl_kw: Named arguments passed to
          ``ssl.SSLContext.load_cert_chain()``
        """
        self.loop = loop or asyncio.get_event_loop()
        self.addr = addr
        self.port = port
        if use_ssl:
            ssl_context = ssl.create_default_context(
                ssl.Purpose.CLIENT_AUTH)
            ssl_context.load_cert_chain(**ssl_kw)
            kw = {'ssl': ssl_context}
        else:
            kw = {}

        coro = self.loop.create_server(self.get_protocol_instance, addr, port,
                                       **kw)
        self.server = self.loop.run_until_complete(coro)
        signal.signal(signal.SIGTERM, self.sync_shutdown)

    def get_protocol_instance(self):
        """Returns an instance of
        :class:`~toxicbuild.slave.protocols.BuildServerProtocol`.
        """

        return self.PROTOCOL_CLS(self.loop)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()

    def start(self):
        """Starts the build server."""
        try:
            self.loop.run_forever()
        finally:
            self.sync_shutdown()

    async def shutdown(self):
        """Overwrite this to handle the shutdown of your server"""

    def sync_shutdown(self):  # pragma no cover
        return self.loop.run_until_complete(self.shutdown())
