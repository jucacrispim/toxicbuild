# -*- coding: utf-8 -*-

from twisted.trial import unittest
from twisted.internet import reactor
from mock import Mock, patch
from toxicbuild import master
from toxicbuild.db.connector import connector


class MasterConfigTestCase(unittest.TestCase):
    @patch.object(master, 'BuildMasterBase', Mock())
    @patch.object(master, 'connector', Mock())
    def setUp(self):
        master.BuildMaster.basedir = 'bla'
        self.master = master.BuildMaster()
        self.master.config.change_sources = [Mock()]
        self.master.umask = None
        self.master.db_loop = False

    def make_reactor(self):
        r = Mock()
        r.callWhenRunning = reactor.callWhenRunning
        return r

    @patch.object(master, 'BuildMasterBase', Mock())
    @patch.object(master, 'connector', Mock())
    def test_toxicbuilddb(self):
        # tests if toxicbuild db is setted correctly
        # on globals
        self.assertTrue(master.TOXICDB)

    @patch.object(master, 'log', Mock())
    def test_startService(self):
        reactor = self.make_reactor()

        d = self.master.startService(_reactor=reactor)
        d.addCallback(lambda _: self.master.stopService())

        @d.addCallback
        def check(_):
            self.failIf(reactor.stop.called)
            self.assertTrue(master.log.msg.called)

        return d

    def test_startService_not_ready_database(self):
        reactor = self.make_reactor()

        def db_setup():
            raise connector.DatabaseNotReadyError()
        self.master.toxicdb.setup = db_setup

        d = self.master.startService(_reactor=reactor)

        @d.addCallback
        def check(_):
            reactor.stop.assert_called()
        return d
