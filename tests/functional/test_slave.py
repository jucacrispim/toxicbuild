# -*- coding: utf-8 -*-

# Copyright 2015 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import json
import os
import unittest
import socket
import subprocess
from tests.functional import REPO_DIR, SCRIPTS_DIR, SLAVE_ROOT_DIR


class DummyBuildClient:

    def __init__(self, addr, port):
        self.addr = addr
        self.port = port
        self.sock = socket.socket()
        self.repo_url = REPO_DIR

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        self.sock.connect((self.addr, self.port))

    def disconnect(self):
        self.sock.close()

    def send(self, data):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.sock.send(data)

    def recv(self):
        r = self.sock.recv(1000)
        return r

    def is_server_alive(self):
        data = {'action': 'healthcheck'}
        self.send(json.dumps(data))
        resp = json.loads(self.recv().decode())
        return not bool(int(resp['code']))

    def build(self, builder_name):
        data = {'action': 'build',
                'body': {'repo_url': self.repo_url,
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master',
                         'builder_name': builder_name}}

        self.send(json.dumps(data))

        build_resp = []
        r = self.recv()

        while r:
            r = json.loads(r.decode())
            build_resp.append(r)
            r = self.recv()

        steps, build_status = build_resp[:-1], build_resp[-1]
        return steps, build_status

    def list_builders(self):
        data = {'action': 'list_builders',
                'body': {'repo_url': self.repo_url,
                         'branch': 'master',
                         'vcs_type': 'git',
                         'named_tree': 'master', }}

        self.send(json.dumps(data))
        r = self.recv()
        r = json.loads(r.decode())
        return r


class SlaveTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.toxicslave = os.path.join(SCRIPTS_DIR, 'toxicslave')
        start_cmd = '{} runserver {} --daemonize'.format(
            cls.toxicslave, SLAVE_ROOT_DIR).split()
        cls.pidfile = os.path.join(SLAVE_ROOT_DIR, 'toxicslave7777.pid')
        subprocess.call(start_cmd)

    @classmethod
    def tearDownClass(cls):
        with open(cls.pidfile, 'r') as fd:
            pid = int(fd.read())

        os.kill(pid, 9)
        os.remove(cls.pidfile)

    def test_healthcheck(self):
        with DummyBuildClient('localhost', 7777) as client:
            self.assertTrue(client.is_server_alive())

    def test_list_builders(self):
        with DummyBuildClient('localhost', 7777) as client:
            builders = client.list_builders()['body']['builders']

        self.assertEqual(builders, ['builder-1'], builders)

    def test_build(self):
        with DummyBuildClient('localhost', 7777) as client:
            step_info, build_status = client.build('builder-1')

        self.assertEqual(len(step_info), 2)
        self.assertEqual(build_status['body']['total_steps'], 1)
        self.assertEqual(build_status['body']['status'], 'success')
