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

    @patch.object(base, 'ConfigReader', Mock())
    def test_createBuildersForCodebase(self):
        base.ConfigReader.return_value.builders = [{'name': 'a'}]
        lastchageid = '2'

        d = base.createBuildersForCodebase(self.instance, lastchageid)

        def check(bnames):
            expected = ['a']
            self.assertEqual(bnames, expected)

        d.addCallback(check)
        return d

    @patch.object(base, 'ConfigReader', Mock())
    def test_createBuildersForCodebases(self):
        base.ConfigReader.return_value.builders = [{'name': 'a'},
                                                   {'name': 'b'}]

        changeids = ['123']
        d = base.createBuildersForCodebases(self.instance, changeids)

        def check(bnames):
            expected = ['a', 'b']
            self.assertEqual(bnames, expected)

        d.addCallback(check)
        return d

    @patch.object(base, 'ConfigReader', Mock())
    @patch.object(base, 'BaseScheduler', Mock())
    def test_addBuildsetForChanges(self):
        base.ConfigReader.return_value.builders = [{'name': 'a'},
                                                   {'name': 'b'}]

        d = base.addBuildsetForChanges(self.instance,
                                       changeids=['123'])

        def check(_):
            bnames = base.BaseScheduler.addBuildsetForChanges.call_args[0][4]
            expected = ['a', 'b']
            self.assertEqual(bnames, expected)

        d.addCallback(check)
        return d
