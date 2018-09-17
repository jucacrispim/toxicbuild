# -*- coding: utf-8 -*-

import os
import socket
import sys
import time
import tornado
from unittest import TestCase
from toxicbuild.core import BaseToxicClient
from toxicbuild.master import create_settings_and_connect
from toxicbuild.slave import create_settings
from toxicbuild.output import (
    create_settings_and_connect as create_settings_output)
from toxicbuild.ui import create_settings as create_settings_ui


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
SOURCE_DIR = os.path.join(DATA_DIR, '..', '..', '..')
SCRIPTS_DIR = os.path.join(SOURCE_DIR, 'scripts')
REPO_DIR = os.path.join(DATA_DIR, 'repo')
SLAVE_ROOT_DIR = os.path.join(DATA_DIR, 'slave')
MASTER_ROOT_DIR = os.path.join(DATA_DIR, 'master')
UI_ROOT_DIR = os.path.join(DATA_DIR, 'ui')
OUTPUT_ROOT_DIR = os.path.join(DATA_DIR, 'output')
PYVERSION = ''.join([str(n) for n in sys.version_info[:2]])

toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')
if not toxicmaster_conf:
    toxicmaster_conf = os.path.join(MASTER_ROOT_DIR, 'toxicmaster.conf')
    os.environ['TOXICMASTER_SETTINGS'] = toxicmaster_conf

toxicslave_conf = os.environ.get('TOXICSLAVE_SETTINGS')
if not toxicslave_conf:
    toxicslave_conf = os.path.join(SLAVE_ROOT_DIR, 'toxicslave.conf')
    os.environ['TOXICSLAVE_SETTINGS'] = toxicslave_conf

toxicweb_conf = os.environ.get('TOXICUI_SETTINGS')
if not toxicweb_conf:
    toxicweb_conf = os.path.join(UI_ROOT_DIR, 'toxicui.conf')
    os.environ['TOXICUI_SETTINGS'] = toxicweb_conf

toxicoutput_conf = os.environ.get('TOXICOUTPUT_SETTINGS')
if not toxicoutput_conf:
    toxicoutput_conf = os.path.join(OUTPUT_ROOT_DIR, 'toxicoutput.conf')
    os.environ['TOXICOUTPUT_SETTINGS'] = toxicoutput_conf

create_settings()
create_settings_ui()
create_settings_and_connect()
create_settings_output()


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


def stop_slave():
    """Stops the test slave"""

    toxicslave_cmd = os.path.join(SCRIPTS_DIR, 'toxicslave')
    pidfile = 'toxicslave{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicslave_cmd, 'stop', SLAVE_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def wait_master_to_be_alive():
    from toxicbuild.master import settings
    HOST = settings.HOLE_ADDR
    PORT = settings.HOLE_PORT
    alive = False
    limit = 20
    step = 0.5
    i = 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        while not alive and i < limit:
            try:
                s.connect((HOST, PORT))
                s.close()
                break
            except Exception:
                alive = False

            time.sleep(step)
            i += step


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

    wait_master_to_be_alive()


def start_scheduler(sleep=0.5):
    """Starts a master scheduler in a new process for tests"""

    toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')

    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicscheduler{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           toxicmaster_cmd, 'start_scheduler', MASTER_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicmaster_conf:
        cmd += ['-c', toxicmaster_conf]

    os.system(' '.join(cmd))
    # time.sleep(sleep)


def start_poller(sleep=0.5):
    """Starts a master poller in a new process for tests"""

    toxicmaster_conf = os.environ.get('TOXICMASTER_SETTINGS')

    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicpoller{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           toxicmaster_cmd, 'start_poller', MASTER_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if toxicmaster_conf:
        cmd += ['-c', toxicmaster_conf]

    os.system(' '.join(cmd))
    # time.sleep(sleep)


def start_output(sleep=0.5):
    """Starts a toxicbuild output instance in a new process for tests"""

    conf = os.path.join(OUTPUT_ROOT_DIR, 'toxicoutput.conf')

    cmd = os.path.join(SCRIPTS_DIR, 'toxicoutput')
    pidfile = 'toxicoutput{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           cmd, 'start', OUTPUT_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile, '--loglevel', 'debug']

    if conf:
        cmd += ['-c', conf]

    os.system(' '.join(cmd))
    # time.sleep(sleep)


def stop_output():
    """Stops the toxicoutput test server"""

    cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicoutput{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', cmd, 'stop', OUTPUT_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def stop_master():
    """Stops the master test server"""

    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicmaster{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicmaster_cmd, 'stop', MASTER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def stop_scheduler():
    """Stops the master's scheduler test server"""

    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicscheduler{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicmaster_cmd, 'stop_scheduler', MASTER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

    os.system(' '.join(cmd))


def stop_poller():
    """Stops the master's poller test server"""

    toxicmaster_cmd = os.path.join(SCRIPTS_DIR, 'toxicmaster')
    pidfile = 'toxicpoller{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', toxicmaster_cmd, 'stop_poller', MASTER_ROOT_DIR,
           '--pidfile', pidfile, '--kill']

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


def start_customwebserver():
    """Start the custom web server for tests """

    custom_cmd = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'custom_webhook.py')
    pidfile = 'customwh{}.pid'.format(PYVERSION)
    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&', 'python',
           custom_cmd, 'start', MASTER_ROOT_DIR, '--daemonize',
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


def stop_customwebserver():
    """Stops the custom web server"""

    custom_cmd = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'custom_webhook.py')
    pidfile = 'customwh{}.pid'.format(PYVERSION)

    cmd = ['export', 'PYTHONPATH="{}"'.format(SOURCE_DIR), '&&',
           'python', custom_cmd, 'stop', MASTER_ROOT_DIR,
           '--pidfile', pidfile]

    os.system(' '.join(cmd))


def start_all():
    start_slave()
    start_poller()
    start_scheduler()
    start_master()
    start_output()
    start_customwebserver()


def stop_all():
    stop_customwebserver()
    stop_scheduler()
    stop_poller()
    stop_master()
    stop_output()
    stop_slave()


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
    def start_custom(cls):
        start_customwebserver()

    @classmethod
    def stop_custom(cls):
        stop_customwebserver()

    @classmethod
    def start_scheduler(cls):
        start_scheduler()

    @classmethod
    def start_poller(cls):
        start_poller()

    @classmethod
    def stop_scheduler(cls):
        stop_scheduler()

    @classmethod
    def stop_poller(cls):
        stop_poller()

    @classmethod
    def start_output(cls):
        start_output()

    @classmethod
    def stop_output(cls):
        stop_output()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.start_slave()
        cls.start_poller()
        cls.start_scheduler()
        cls.start_master()
        cls.start_output()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.stop_scheduler()
        cls.stop_poller()
        cls.stop_master()
        cls.stop_output()
        cls.stop_slave()

    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.instance()


STREAM_EVENT_TYPES = ['build_added', 'build_started', 'build_finished',
                      'step_started', 'step_finished', 'step_output_arrived',
                      'repo_status_changed', 'repo_added']


class DummyMasterHoleClient(BaseToxicClient):

    def __init__(self, user, *args, **kwargs):
        kwargs['use_ssl'] = True
        kwargs['validate_cert'] = False
        super().__init__(*args, **kwargs)
        self.user = user

    async def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'user_id': str(self.user.id),
                'token': '123'}
        await self.write(data)
        response = await self.get_response()
        return response['body'][action]

    async def create_slave(self, slave_port):
        action = 'slave-add'
        body = {'slave_name': 'test-slave',
                'slave_host': 'localhost',
                'slave_port': slave_port,
                'slave_token': '123',
                'owner_id': str(self.user.id),
                'use_ssl': True,
                'validate_cert': False}

        resp = await self.request2server(action, body)
        return resp

    async def create_repo(self):
        action = 'repo-add'
        body = {'repo_name': 'test-repo', 'repo_url': REPO_DIR,
                'vcs_type': 'git', 'update_seconds': 1,
                'slaves': ['test-slave'],
                'owner_id': str(self.user.id)}

        resp = await self.request2server(action, body)

        return resp

    async def wait_clone(self):
        await self.write({'action': 'stream', 'token': '123',
                          'body': {'event_types': STREAM_EVENT_TYPES},
                          'user_id': str(self.user.id)})
        while True:
            r = await self.get_response()
            body = r['body'] if r else {}
            try:
                event = body['event_type']
                if event == 'repo_status_changed':
                    break
            except KeyError:
                pass

    async def start_build(self, builder='builder-1'):

        action = 'repo-start-build'
        body = {'repo_name_or_id': 'toxic/test-repo',
                'branch': 'master'}
        if builder:
            body['builder_name'] = builder
        resp = await self.request2server(action, body)

        return resp

    async def wait_build_complete(self):
        await self.write({'action': 'stream', 'token': '123',
                          'body': {'event_types': STREAM_EVENT_TYPES},
                          'user_id': str(self.user.id)})

        # this ugly part here it to wait for the right message
        # If we don't use this we may read the wrong message and
        # the test will fail.
        while True:
            response = await self.get_response()
            body = response['body'] if response else {}
            if body.get('event_type') == 'build_finished':
                has_sleep = False
                for step in body['steps']:
                    if step['command'] == 'sleep 3':
                        has_sleep = True

                if not has_sleep:
                    break
        return response
