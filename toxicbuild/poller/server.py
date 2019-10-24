# -*- coding: utf-8 -*-

from toxicbuild.core.protocol import BaseToxicProtocol


class PollerServer(BaseToxicProtocol):

    async def client_connected(self):
        assert self.action == 'poll', 'Bad Action'
