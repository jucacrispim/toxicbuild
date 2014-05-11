# -*- coding: utf-8 -*-

import unittest
from mock import Mock
from toxicbuild.process import factory


class DynamicBuildFactoryTestCase(unittest.TestCase):
    def setUp(self):
        venv_path = 'some/where/'
        pyversion = '/usr/bin/python3.4'
        self.factory = factory.DynamicBuildFactory(venv_path, pyversion)

    def test_newBuild(self):
        venv_path = 'some/where/'
        pyversion = '/usr/bin/python3.4'
        requests = [Mock()]
        b = self.factory.newBuild(requests)

        self.assertTrue(b.venv_path == venv_path and b.pyversion == pyversion)
