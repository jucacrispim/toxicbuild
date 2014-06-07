# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from buildbot.schedulers.forcesched import ForceScheduler
from toxicbuild.process import builder


class CreateBuildersTestCase(unittest.TestCase):
    def test_createBuilderFromDict(self):
        master = Mock()
        s1, s2 = Mock(), Mock()
        s1.slavename, s2.slavename = 's1', 's2'
        master.config.slaves = [s1, s2]
        bdict = {'name': 'b1'}

        returned = builder.createBuilderFromDict(master, bdict)

        self.assertTrue(returned)

    @patch.object(builder.log, 'msg', Mock())
    def test_createBuildersFromConfig(self):
        master = Mock()
        s1, s2 = Mock(), Mock()
        s1.slavename, s2.slavename = 's1', 's2'
        master.config.slaves = [s1, s2]
        master.config.schedulers = {}
        master.botmaster.builderNames = ['b1']
        config = Mock()
        config.builders = [{'name': 'b1'},
                           {'name': 'b2', 'steps': ['ls']}]

        bnames = builder.createBuildersFromConfig(master, config)
        expected = ['b1', 'b2']

        self.assertTrue(bnames, expected)
        self.assertEqual(len(builder.log.msg.call_args_list), 1)

    def test_setInForceScheduler(self):
        master = Mock()
        sched = ForceScheduler('scheduler', ['a'])
        sched.builderNames = Mock()
        master.config.schedulers = {'fs': sched}
        bmock = Mock()
        builder.setInForceScheduler(master, bmock)

        self.assertTrue(sched.builderNames.append.called)
