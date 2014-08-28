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


class StartToxicBuildOptionsTest(unittest.TestCase):
    def test_start_toxicbuild_options(self):
        opt = runner.StartToxicBuildOptions()

        flags = [['quiet', 'q', 'Do not emit the commands being run']]

        everything_ok = flags == opt.optFlags

        self.assertTrue(everything_ok)

    def test_getSynopsis(self):
        opt = runner.StartToxicBuildOptions()
        self.assertTrue(opt.getSynopsis())


class StopToxicBuildOptionsTest(unittest.TestCase):
    def test_stop_toxicbuild_options(self):
        opt = runner.StopToxicBuildOptions()

        flags = [['quiet', 'q', 'Do not emit the commands being run']]

        everything_ok = flags == opt.optFlags

        self.assertTrue(everything_ok)

    def test_getSynopsis(self):
        opt = runner.StopToxicBuildOptions()
        self.assertTrue(opt.getSynopsis())
