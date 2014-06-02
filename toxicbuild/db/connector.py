# -*- coding: utf-8 -*-

from twisted.python import log
from twisted.internet import defer
from twisted.application import service
from buildbot import config
from buildbot.db import connector, enginestrategy, pool
from toxicbuild.db import model
from toxicbuild.db.revisionconfig import RevisionConfigConnectorComponent


class DBConnector(connector.DBConnector):
    # lazy copy from bb connector

    def __init__(self, master, basedir):
        service.MultiService.__init__(self)
        self.setName('toxicdb')
        self.master = master
        self.basedir = basedir

        # not configured yet - we don't build an engine until the first
        # reconfig
        self.configured_url = None

        # set up components
        self._engine = None  # set up in reconfigService
        self.pool = None  # set up in reconfigService
        self.model = model.Model(self)
        self.revisionconfig = RevisionConfigConnectorComponent(self)

    def setup(self, verbose=True):
        db_url = self.configured_url = self.master.config.db[
            'toxicbuild_db_url']

        log.msg("Setting up database with URL %r" % (db_url,))

        # set up the engine and pool
        self._engine = enginestrategy.create_engine(db_url,
                                                    basedir=self.basedir)
        self.pool = pool.DBThreadPool(self._engine, verbose=verbose)

        # oh, yeah! all that nice check_version stuff is missing...
        return defer.succeed(None)

    def reconfigService(self, new_config):
        # double-check -- the master ensures this in config checks
        assert self.configured_url == new_config.db['toxicbuild_db_url']

        return config.ReconfigurableServiceMixin.reconfigService(self,
                                                                 new_config)
