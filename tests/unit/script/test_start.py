# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from toxicbuild.scripts import start


class StartToxicbuildTest(unittest.TestCase):
    @patch.object(start.subprocess, 'call', Mock(return_value=0))
    def test_start(self):
        config = {'basedir': '~/some/dir',
                  'quiet': True}
        start.start(config)

        self.assertEqual(len(start.subprocess.call.call_args_list), 2)

    @patch.object(start.subprocess, 'call', Mock(return_value=1))
    def test_start_with_errors_on_master(self):
        config = {'basedir': '~/some/dir',
                  'quiet': True}
        ret = start.start(config)
        self.assertTrue(ret)

    @patch.object(start.subprocess, 'call', Mock(side_effect=[0, 1]))
    def test_start_with_errors_on_slave(self):
        config = {'basedir': '~/some/dir',
                  'quiet': True}
        ret = start.start(config)
        self.assertTrue(ret)
