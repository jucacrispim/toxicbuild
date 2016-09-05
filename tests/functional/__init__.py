# -*- coding: utf-8 -*-

import os
import sys
import time
import tornado
from tornado.testing import AsyncTestCase
from toxicbuild.master import create_settings_and_connect
from toxicbuild.slave import create_settings
from toxicbuild.ui import create_settings as create_settings_ui

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCE_DIR = os.path.join(DATA_DIR, '..', '..', '..')
SCRIPTS_DIR = os.path.join(SOURCE_DIR, 'scripts')
REPO_DIR = os.path.join(DATA_DIR, 'repo')
SLAVE_ROOT_DIR = os.path.join(DATA_DIR, 'slave')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')
PYVERSION = ''.join([str(n) for n in sys.version_info[:2]])


create_settings()
create_settings_ui()
create_settings_and_connect()


class BaseFunctionalTest(AsyncTestCase):

    """An AsyncTestCase that starts a master and a slave process on
    setUpClass and stops it on tearDownClass"""

    @classmethod
    def start_slave(cls):
        """Starts a slave in a new process."""

        toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
        pidfile = 'toxicslave{}.pid'.format(PYVERSION)
        toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
               toxicslave_cmd, 'start', SLAVE_ROOT_DIR, '--daemonize',
               '--pidfile', pidfile]

        if toxicslave_conf:
            cmd += ['-c', toxicslave_conf]

        os.system(' '.join(cmd))

    @classmethod
    def stop_slave(cls):

        toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
        pidfile = 'toxicslave{}.pid'.format(PYVERSION)
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
               'python', toxicslave_cmd, 'stop', SLAVE_ROOT_DIR,
               '--pidfile', pidfile]

        os.system(' '.join(cmd))

    @classmethod
    def start_master(cls):
        toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')
        toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
        pidfile = 'toxicmaster{}.pid'.format(PYVERSION)
        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
               toxicmaster_cmd, 'start', MASTER_ROOT_DIR, '--daemonize',
               '--pidfile', pidfile]

        if toxicmaster_conf:
            cmd += ['-c', toxicmaster_conf]

        os.system(' '.join(cmd))

    @classmethod
    def stop_master(cls):
        toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
        pidfile = 'toxicmaster{}.pid'.format(PYVERSION)

        cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
               'python', toxicmaster_cmd, 'stop', MASTER_ROOT_DIR,
               '--pidfile', pidfile]

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
