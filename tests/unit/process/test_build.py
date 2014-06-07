# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from toxicbuild.process import build


class DynamicBuildTestCase(unittest.TestCase):
    def setUp(self):
        requests = [Mock()]
        builder = Mock()
        builder.name = 'b1'
        self.build = build.DynamicBuild(requests)
        self.build.setBuilder(builder)
        self.build.venv_path = 'bla/ble/'

    def test_create_step(self):
        cmd = {'name': 'nice',
               'command':
               ['sh', './some_nice_script.sh', '--do-the-right-way']}
        path = 'bla/ble/bin'
        expected = {'command': cmd['command'],
                    'name': 'nice',
                    'env': {'PATH': [path, '${PATH}']}}

        st = self.build.create_step(cmd)
        called = st.kwargs

        self.assertEqual(expected, called)

    def test_get_step_env(self):
        path = 'bla/ble/bin'
        expected = {'PATH': [path, '${PATH}']}
        returned = self.build.get_step_env()

        self.assertEqual(expected, returned)

    @patch.object(build.master, 'TOXICDB', Mock())
    @patch.object(build.Build, 'setupBuild', Mock())
    @patch.object(build.DynamicBuild, 'getProperty', Mock())
    def test_setupBuild(self):
        revconf = Mock()
        revconf.config = """
builders = [{'name': 'b1',
             'steps': [{'name': 'run tests',
                 'command': 'python setup.py test --settings=settings_test'}]}]
"""
        build.master.TOXICDB.revisionconfig._getRevisionConfig.\
            return_value = revconf

        self.build.setupBuild()
        # 4 steps. 3 from get_default_steps and 1 from config file
        self.assertEqual(len(self.build.stepFactories), 4)

    @patch.object(build.master, 'TOXICDB', Mock())
    @patch.object(build.Build, 'setupBuild', Mock())
    @patch.object(build.DynamicBuild, 'getProperty', Mock())
    def test_setupBuild_with_not_config_ok(self):
        revconf = Mock()
        revconf.config = """
= [{'name': 'run tests',
    'command': 'python setup.py test --settings=settings_test'}]
"""
        build.master.TOXICDB.revisionconfig.getRevisionConfig.\
            return_value = revconf

        self.build.setupBuild()
        # BombStep!
        self.assertEqual(len(self.build.stepFactories), 1)


class BombStepTestCase(unittest.TestCase):
    def test_raises(self):
        exception = KeyError
        b = build.BombStep(exception=exception)
        with self.assertRaises(KeyError):
            b.startStep()
