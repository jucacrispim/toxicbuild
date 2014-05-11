# -*- coding: utf-8 -*-

import unittest
from toxicbuild.scripts import runner


class CreateToxicbuildOptionsTestCase(unittest.TestCase):
    def test_create_toxicbuild_options(self):
        opt = runner.CreateToxicbuildOptions()

        flags = [['quiet', 'q', 'Do not emit the commands being run']]
        h = "which DB to use for scheduler/status state. See below for syntax."
        params = [
            ["toxicbuild-db", None, "sqlite:///toxicbuild.sqlite", h]
        ]

        everything_ok = flags == opt.optFlags and params == opt.optParameters

        self.assertTrue(everything_ok)

    def test_getSynopsis(self):
        opt = runner.CreateToxicbuildOptions()

        expected = 'Usage: toxicbuild create <basedir>'
        returned = opt.getSynopsis()

        self.assertEqual(expected, returned)
