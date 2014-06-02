# -*- coding: utf-8 -*-

import os
import mock
from twisted.internet import defer
from twisted.trial import unittest
from buildbot import config
from buildbot.test.util import db
from buildbot.test.fake import fakemaster
from toxicbuild.db import connector


class DBConnectorTestCase(db.RealDatabaseMixin, unittest.TestCase):
    """
    Basic tests of the DBConnector class - all start with an empty DB
    """

    # yeah! code and tests stolen from bb

    @defer.inlineCallbacks
    def setUp(self):
        yield self.setUpRealDatabase(table_names=['revision_config'])

        self.master = fakemaster.make_master()
        self.master.config = config.MasterConfig()
        self.db = connector.DBConnector(self.master,
                                        os.path.abspath('basedir'))

    @defer.inlineCallbacks
    def tearDown(self):
        yield self.db.stopService()
        yield self.tearDownRealDatabase()

    @defer.inlineCallbacks
    def startService(self):
        self.master.config.db['toxicbuild_db_url'] = self.db_url
        yield self.db.setup()
        self.db.startService()
        yield self.db.reconfigService(self.master.config)

    # tests

    def test_has_revisionconfig(self):
        # tests if revisionconfig attribute is present
        d = self.startService()

        @d.addCallback
        def check(_):
            self.assertTrue(hasattr(self.db, 'revisionconfig'))

        return d
