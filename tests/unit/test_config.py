# -*- coding: utf-8 -*-

import unittest
from toxicbuild.config import ConfigReader, DynamicBuilderConfig
from toxicbuild.process.factory import DynamicBuildFactory


class ConfigReaderTestCase(unittest.TestCase):
    def setUp(self):
        self.configstr = """
[{'name': 'run tests',
  'command': 'python setup.py test'},

 {'name': 'check something',
  'command': 'sh ./check_something.sh'}]
"""

        self.config = ConfigReader(self.configstr)

    def test_parse_steps(self):
        expected = [{'name': 'run tests', 'command':
                     ['python', 'setup.py', 'test']},
                    {'name': 'check something', 'command':
                     ['sh', './check_something.sh']}]

        steps = self.config.parse_steps()

        self.assertEqual(expected, steps)


class ToxicbuilderConfigTestCase(unittest.TestCase):
    def test_create_builder(self):
        builder = DynamicBuilderConfig(venv_path='venv',
                                       pyversion='/usr/bin/python3',
                                       name='toxicbuilder',
                                       slavenames=['slave1'])

        self.assertTrue(isinstance(builder.factory, DynamicBuildFactory))
