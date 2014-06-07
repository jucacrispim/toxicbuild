# -*- coding: utf-8 -*-

import unittest
from toxicbuild import config
from toxicbuild.config import ConfigReader, DynamicBuilderConfig
from toxicbuild.process.factory import DynamicBuildFactory


class ConfigReaderTestCase(unittest.TestCase):
    def setUp(self):
        self.configstr = """
builders = [{'name': 'b1',
             'steps': [{'name': 'run tests',
                        'command': 'python setup.py test'},

                       {'name': 'check something',
                        'command': 'sh ./check_something.sh'}]}]
"""

        self.config = ConfigReader(self.configstr)

    def test_getSteps(self):
        expected = [{'name': 'run tests', 'command':
                     ['python', 'setup.py', 'test']},
                    {'name': 'check something', 'command':
                     ['sh', './check_something.sh']}]

        builder = {'name': 'b1',
                   'steps': [{'name': 'run tests',
                              'command': 'python setup.py test'},
                             {'name': 'check something',
                              'command': 'sh ./check_something.sh'}]}

        steps = self.config._getSteps(builder)

        self.assertEqual(expected, steps)

    def test_getBuilders(self):

        expected = [{'name': 'b1',
                     'steps': [{'name': 'run tests',
                                'command': ['python', 'setup.py', 'test']},
                               {'name': 'check something',
                                'command': ['sh', './check_something.sh']}]}]

        builders = self.config.getBuilders()
        self.assertEqual(builders, expected)


class DynamcBuilderConfigTestCase(unittest.TestCase):
    def test_create_builder(self):
        builder = DynamicBuilderConfig(venv_path='venv',
                                       pyversion='/usr/bin/python3',
                                       name='toxicbuilder',
                                       slavenames=['slave1'])

        self.assertTrue(isinstance(builder.factory, DynamicBuildFactory))


class MasterConfigTestCase(unittest.TestCase):
    def setUp(self):
        self.masterconfig = config.MasterConfig()

    def test_load_db(self):
        filename = 'master.cfg'
        config_dict = {'db': {'toxicbuild_db_url': 'sqlite:///bla.sqlite'}}
        self.masterconfig.db = {'db_poll_interval': 1}
        self.masterconfig.load_db(filename, config_dict)

        self.assertEqual(self.masterconfig.db['toxicbuild_db_url'],
                         'sqlite:///bla.sqlite')
