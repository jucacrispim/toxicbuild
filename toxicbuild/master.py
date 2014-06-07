# -*- coding: utf-8 -*-

from twisted.python import log
from twisted.internet import defer, reactor
from buildbot.master import BuildMaster as BuildMasterBase
from toxicbuild import config
from toxicbuild.db import connector

# tragic hack to gimme access to a db connector every where, any time.
TOXICDB = None


class BuildMaster(BuildMasterBase):
    def __init__(self, *args, **kwargs):
        BuildMasterBase.__init__(self, *args, **kwargs)

        self.config = config.MasterConfig()

        self.toxicdb = connector.DBConnector(self, self.basedir)
        self.toxicdb.setServiceParent(self)
        global TOXICDB
        TOXICDB = self.toxicdb

    @defer.inlineCallbacks
    def startService(self, _reactor=reactor):
        BuildMasterBase.startService(self, _reactor=reactor)
        try:
            yield self.toxicdb.setup()
        except connector.connector.DatabaseNotReadyError:
            # (message was already logged)
            _reactor.stop()
            return

        # polling early to have some builders as soon as posible
        for poller in self.config.change_sources:
            yield poller.doPoll()

        log.msg("Toxicbuild is running")
