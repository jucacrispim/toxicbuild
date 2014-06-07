# -*- coding: utf-8 -*-

from twisted.trial import unittest
from toxicbuild.schedulers import basic


class BasicSchedulersTestCase(unittest.TestCase):

    def test_ToxicSingleBranchScheduler(self):
        self.assertTrue(basic.ToxicSingleBranchScheduler.addBuildsetForChanges)

    def test_ToxicAnyBranchScheduler(self):
        self.assertTrue(basic.ToxicAnyBranchScheduler.addBuildsetForChanges)
