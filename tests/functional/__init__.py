# -*- coding: utf-8 -*-

import os
import sys
import time
import tornado
from unittest import TestCase
from toxicbuild.master import create_settings_and_connect
from toxicbuild.slave import create_settings
from toxicbuild.ui import create_settings as create_settings_ui

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCE_DIR = os.path.join(DATA_DIR, '..', '..', '..')
SCRIPTS_DIR = os.path.join(SOURCE_DIR, 'scripts')
REPO_DIR = os.path.join(DATA_DIR, 'repo')
SLAVE_ROOT_DIR = os.path.join(DATA_DIR, 'slave')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')
UI_ROOT_DIR = os.path.join(DATA_DIR, 'ui')
PYVERSION = ''.join([str(n) for n in sys.version_info[:2]])


create_settings()
create_settings_ui()
create_settings_and_connect()


def start_slave(sleep=0.5):
    """Starts an slave server in a new process for tests"""

    toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
    pidfile = 'toxicslave{}.pid'.format(PYVERSION)
    toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           toxicslave_cmd, 'start', SLAVE_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicslave_conf:
        cmd += ['-c', toxicslave_conf]

    os.system(' '.join(cmd))
    time.sleep(sleep)


def stop_slave():
    """Stops the test slave"""

    toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
    pidfile = 'toxicslave{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicslave_cmd, 'stop', SLAVE_ROOT_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


def start_master(sleep=0.5):
    """Starts a master server in a new process for tests"""

    toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')
    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           toxicmaster_cmd, 'start', MASTER_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicmaster_conf:
        cmd += ['-c', toxicmaster_conf]

    os.system(' '.join(cmd))
    time.sleep(sleep)


def stop_master():
    """Stops the master test server"""

    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicmaster_cmd, 'stop', MASTER_ROOT_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


def start_webui():
    """Start a web interface for tests """

    toxicweb_conf = os.environ.get('TOXICUI_SETTINGS')
    toxicweb_cmd = os.path.join(SCRIPTS_DIR, 'toxicweb')
    pidfile = 'toxicui{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           toxicweb_cmd, 'start', UI_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile]

    if toxicweb_conf:
        cmd += ['-c', toxicweb_conf]

    os.system(' '.join(cmd))


def stop_webui():
    """Stops the test web interface"""

    toxicweb_cmd = os.path.join(SCRIPTS_DIR, 'toxicweb')
    pidfile = 'toxicui{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicweb_cmd, 'stop', UI_ROOT_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


class BaseFunctionalTest(TestCase):

    """An AsyncTestCase that starts a master and a slave process on
    setUpClass and stops it on tearDownClass"""

    @classmethod
    def start_slave(cls):
        start_slave()

    @classmethod
    def stop_slave(cls):
        stop_slave()

    @classmethod
    def start_master(cls):
        start_master()

    @classmethod
    def stop_master(cls):
        stop_master()

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
