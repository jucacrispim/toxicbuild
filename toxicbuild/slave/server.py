# -*- coding: utf-8 -*-

import asyncio
import signal
import ssl
from toxicbuild.core.utils import log, LoggerMixin
from toxicbuild.slave.protocols import BuildServerProtocol

__doc__ = """This module implements a build server. Receives requests from
the toxicbuild master and handles it using
:class:`~toxicbuild.slave.protocols.BuildServerProtocol`.

Usage
`````

.. code-block:: python

    with BuildServer(addr, port, use_ssl, **ssl_kw) as server:
        server.start()

"""


class BuildServer(LoggerMixin):
    """A server that receives build requests from a toxicmaster instance."""

    def __init__(self, addr='0.0.0.0', port=7777, loop=None,
                 use_ssl=False, **ssl_kw):
        """:param addr: Address from which the server is allowed to receive
        requests. If ``0.0.0.0``, receives requests from all addresses.
        :param port: The port for the slave to listen.
        :param loop: A main loop. If none, ``asyncio.get_event_loop()``
          will be used.
        :param use_ssl: Indicates is the connection uses ssl or not.
        :param ssl_kw: Named arguments passed to
          ``ssl.SSLContext.load_cert_chain()``
        """
        self.protocol = BuildServerProtocol
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
        :class:`~toxicbuild.slave.protocols.BuildServerProtocol`."""

        return self.protocol(self.loop)

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
            self.loop.run_until_complete(self.shutdown())

    async def shutdown(self):
        """Shuts down the build server. Waits for the current running
        builds to complete."""

        self.log('Shutting down')
        self.protocol._is_shuting_down = True
        while self.protocol._clients_connected > 0:
            self.log('Clients connected: {}'.format(
                self.protocol._clients_connected), level='debug')
            await asyncio.sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        """Synchronous version of
        :meth:`~toxicbuild.slave.server.BuidServer.shutdown`."""

        self.loop.run_until_complete(self.shutdown())


def run_server(addr='0.0.0.0', port=7777, loop=None, use_ssl=False, **ssl_kw):
    log('Serving at {}'.format(port))
    with BuildServer(addr, port, loop, use_ssl, **ssl_kw) as server:
        server.start()
