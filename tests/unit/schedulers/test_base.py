# -*- coding: utf-8 -*-

from twisted.trial import unittest
from mock import Mock, patch
from toxicbuild.schedulers import base


class AddBuildsetForChangesTestCase(unittest.TestCase):
    def setUp(self):
        self.instance = Mock()
        self.instance.master.botmaster.builderNames = []
        s1, s2 = Mock(), Mock()
        s1.slavename, s2.slavename = 's1', 's2'
        self.instance.master.config.slaves = [s1, s2]
        self.instance.master.config.schedulers = {}
        self.instance.codebases = ['']
        self.instance\
            .master.db.changes.getChange\
                              .return_value = {'branch': 'master',
                                               'repository': 'git@bla',
                                               'revision': '123',
                                               'codebase': '',
                                               'changeid': 'sdf'}

    def test_getBuildersForChanges(self):
        revconf_mock = Mock()
        revconf_mock.config = """
builders = [{'name': 'b1',
             'branch': 'master',
             'steps': [{'name': 'step 1',
                       'command': 'ls -la'}]}]
"""
        self.instance.master.toxicdb.revisionconfig\
            .getRevisionConfig.return_value = revconf_mock

        d = base.getBuildersForChanges(self.instance, ['asdf', 'qwer'])

        def check(builders):
            expected = ['b1']
            bnames = [b['name'] for b in builders]
            self.assertEqual(bnames, expected)

        d.addCallback(check)
        return d

    @patch.object(base, 'ConfigReader', Mock())
    def test_getLastChange(self):
        base.ConfigReader.return_value.builders = [{'name': 'a'},
                                                   {'name': 'b'}]

        changeids = ['123', 'sdf']
        d = base.getLastChange(self.instance, changeids)

        def check(_):
            called = self.instance.master.db.changes.getChange.call_args[0][0]
            self.assertEqual(called, 'sdf')

        d.addCallback(check)
        return d

    @patch.object(base, 'ConfigReader', Mock())
    @patch.object(base, 'BaseScheduler', Mock())
    def test_addBuildsetForChanges(self):
        base.ConfigReader.return_value.getBuildersForBranch\
                                      .return_value = [{'name': 'a'},
                                                       {'name': 'b'}]

        d = base.addBuildsetForChanges(self.instance,
                                       changeids=['123'])

        def check(_):
            bnames = base.BaseScheduler.addBuildsetForChanges.call_args[0][4]
            expected = ['a', 'b']
            self.assertEqual(bnames, expected)

        d.addCallback(check)
        return d
