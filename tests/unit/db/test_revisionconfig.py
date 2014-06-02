# -*- coding: utf-8 -*-

from datetime import datetime
from twisted.trial import unittest
from tests.util import connector_component
from tests.fake import fakedb
from toxicbuild.db import model
from toxicbuild.db.revisionconfig import RevisionConfigConnectorComponent


class TestRevisionConfigConnectorComponent(
        connector_component.ConnectorComponentMixin,
        unittest.TestCase):

    def setUp(self):
        d = self.setUpConnectorComponent(
            table_names=['revision_config'])

        def finish_setup(_):
            self.db.revisionconfig = RevisionConfigConnectorComponent(self.db)
            self.db.model = model.Model(self.db)
        d.addCallback(finish_setup)

        return d

    def tearDown(self):
        return self.tearDownConnectorComponent()

    def test_getRevisionConfig(self):
        # tests if the last revision is taken when no revision is passed
        fake_revconf = fakedb.RevisionConfig(
            repourl='git@some.where', revision='123qweasd', branch='master',
            config='steps=[]', timestamp=datetime.now())

        d = self.insertTestData([fake_revconf])
        d.addCallback(lambda _: self.db.revisionconfig.getRevisionConfig(
            'master', 'git@some.where'))

        def check(ret):
            self.assertEqual(ret.revision, '123qweasd')

        d.addCallback(check)
        return d

    def test_saveRevisionConfig(self):
        d = self.db.revisionconfig.saveRevisionConfig(
            revision='123qweasd', branch='master', repourl='git@some.where',
            config='steps=[]')

        d.addCallback(lambda _: self.db.revisionconfig.getRevisionConfig(
            'master', 'git@some.where', revision='123qweasd'))

        def check(ret):
            self.assertEqual(ret.config, 'steps=[]')

        d.addCallback(check)
        return d
