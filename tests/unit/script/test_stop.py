# -*- coding: utf-8 -*-

import unittest
from mock import Mock, patch
from toxicbuild.scripts import stop


class StopToxicbuildTest(unittest.TestCase):
    @patch.object(stop.subprocess, 'call', Mock(return_value=0))
    def test_stop(self):
        config = {'basedir': '~/some/dir',
                  'quiet': True}
        stop.stop(config)

        self.assertEqual(len(stop.subprocess.call.call_args_list), 2)

    @patch.object(stop.subprocess, 'call', Mock(return_value=1))
    def test_stop_with_errors_on_master(self):
        config = {'basedir': '~/some/dir',
                  'quiet': True}
        ret = stop.stop(config)
        self.assertTrue(ret)

    @patch.object(stop.subprocess, 'call', Mock(side_effect=[0, 1]))
    def test_stop_with_errors_on_slave(self):
        config = {'basedir': '~/some/dir',
                  'quiet': True}
        ret = stop.stop(config)
        self.assertTrue(ret)
