# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from buildbot.schedulers.forcesched import ForceScheduler
from toxicbuild.process import builder


class BuilderManagerTest(unittest.TestCase):
    def setUp(self):
        master = Mock()
        s1, s2 = Mock(), Mock()
        s1.slavename, s2.slavename = 's1', 's2'
        master.config.slaves = [s1, s2]
        master.config.schedulers = {}
        master.botmaster.builderNames = ['b1', 'b3']
        master.botmaster.builders = {'b1': Mock(),
                                     'b3': Mock()}
        config = Mock()
        config.builders = [{'name': 'b1'},
                           {'name': 'b2', 'steps': ['ls']}]

        self.manager = builder.BuilderManager(master, config)


    def test_createBuilderFromDict(self):
        bdict = {'name': 'b1'}

        returned = self.manager.createBuilderFromDict(bdict)

        self.assertTrue(returned)

    @patch.object(builder.log, 'msg', Mock())
    def test_createNewBuilders(self):

        bnames = self.manager.createNewBuilders()
        expected = ['b1', 'b2']

        self.assertTrue(bnames, expected)
        self.assertEqual(len(builder.log.msg.call_args_list), 1)

    @patch.object(builder.log, 'msg', Mock())
    def test_removeOldBuilders(self):
        bnames = self.manager.removeOldBuilders()
        expected = ['b3']

        self.assertTrue(bnames, expected)
        self.assertEqual(len(builder.log.msg.call_args_list), 1)

    def test_addToForceScheduler(self):
        sched = ForceScheduler('scheduler', ['a'])
        sched.builderNames = Mock()
        self.manager.master.config.schedulers = {'fs': sched}
        bmock = Mock()
        self.manager.addToForceScheduler(bmock)

        self.assertTrue(sched.builderNames.append.called)

    def test_updateSlaves(self):
        self.manager.updateSlaves()
        self.assertTrue(
            self.manager.master.config.slaves[0].updateSlave.called)
        self.assertTrue(
            self.manager.master.config.slaves[1].updateSlave.called)

    def test_updateBuilders(self):
        builders, removed = self.manager.updateBuilders()
        exp_builders, exp_removed = ['b1', 'b2'], ['b3']
        self.assertEqual((builders, removed), (exp_builders, exp_removed))
