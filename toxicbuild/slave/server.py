# -*- coding: utf-8 -*-

import asyncio
from toxicbuild.core.server import ToxicServer
from toxicbuild.core.utils import log
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


class BuildServer(ToxicServer):
    """A server that receives build requests from a toxicmaster instance."""

    PROTOCOL_CLS = BuildServerProtocol

    async def shutdown(self):
        """Shuts down the build server. Waits for the current running
        builds to complete."""

        self.log('Shutting down')
        self.PROTOCOL_CLS._is_shuting_down = True
        while self.PROTOCOL_CLS._clients_connected > 0:
            self.log('Clients connected: {}'.format(
                self.PROTOCOL_CLS._clients_connected), level='debug')
            await asyncio.sleep(0.5)


def run_server(addr='0.0.0.0', port=7777, loop=None, use_ssl=False,
               **ssl_kw):  # pragma no cover
    log('Serving at {}'.format(port))
    with BuildServer(addr, port, loop, use_ssl, **ssl_kw) as server:
        server.start()
