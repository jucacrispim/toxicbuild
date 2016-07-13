# -*- coding: utf-8 -*-

import os
import time
import tornado
from tornado.testing import AsyncTestCase

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCE_DIR = os.path.join(DATA_DIR, '..', '..', '..')
SCRIPTS_DIR = os.path.join(SOURCE_DIR, 'scripts')
REPO_DIR = os.path.join(DATA_DIR, 'repo')
SLAVE_ROOT_DIR = os.path.join(DATA_DIR, 'slave')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')


class BaseFunctionalTest(AsyncTestCase):

    """An AsyncTestCase that starts a master and a slave process on
    setUpClass and stops it on tearDownClass"""

    @classmethod
    def start_slave(cls):
        """Starts a slave in a new process."""

        toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
        toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
               toxicslave_cmd, 'start', SLAVE_ROOT_DIR, '--daemonize']

        if toxicslave_conf:
            cmd += ['-c', toxicslave_conf]

        os.system(' '.join(cmd))

    @classmethod
    def stop_slave(cls):
        toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
               'python', toxicslave_cmd, 'stop', SLAVE_ROOT_DIR]

        os.system(' '.join(cmd))

    @classmethod
    def start_master(cls):
        toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')
        toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
               toxicmaster_cmd, 'start', MASTER_ROOT_DIR, '--daemonize']

        if toxicmaster_conf:
            cmd += ['-c', toxicmaster_conf]

        os.system(' '.join(cmd))

    @classmethod
    def stop_master(cls):
        toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')

        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
               'python', toxicmaster_cmd, 'stop', MASTER_ROOT_DIR]

        os.system(' '.join(cmd))

        super().tearDownClass()

    @classmethod
    def setUpClass(cls):

        super().setUpClass()
        cls.start_slave()
        cls.start_master()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.stop_master()
        cls.stop_slave()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()
