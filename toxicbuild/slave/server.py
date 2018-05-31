# -*- coding: utf-8 -*-

import asyncio
import signal
from toxicbuild.core.utils import log, LoggerMixin
from toxicbuild.slave.protocols import BuildServerProtocol


class BuildServer(LoggerMixin):

    def __init__(self, addr='0.0.0.0', port=7777):
        self.protocol = BuildServerProtocol
        self.loop = asyncio.get_event_loop()
        self.addr = addr
        self.port = port
        coro = self.loop.create_server(self.get_protocol_instance, addr,  port)
        self.server = self.loop.run_until_complete(coro)
        signal.signal(signal.SIGTERM, self.sync_shutdown)

    def get_protocol_instance(self):
        return self.protocol(self.loop)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.close()
        self.loop.run_until_complete(self.server.wait_closed())
        self.loop.close()

    def start(self):
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.shutdown())

    async def shutdown(self):
        self.log('Shutting down')
        self.protocol._is_shuting_down = True
        while self.protocol._clients_connected > 0:
            self.log('Clients connected: {}'.format(
                self.protocol._clients_connected), level='debug')
            await asyncio.sleep(0.5)

    def sync_shutdown(self, signum=None, frame=None):
        self.loop.run_until_complete(self.shutdown())


def run_server(addr='0.0.0.0', port=7777):
    log('Serving at {}'.format(port))
    with BuildServer(addr, port) as server:
        server.start()
