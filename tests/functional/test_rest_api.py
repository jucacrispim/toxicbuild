# -*- coding: utf-8 -*-
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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

import base64
import json
from unittest import TestCase
import bcrypt
import requests
from pyrocumulus.auth import AccessToken
from pyrocumulus.utils import bcrypt_string
from toxicbuild.master.repository import Repository as RepoDBModel
from toxicbuild.master.slave import Slave as SlaveDBModel
from toxicbuild.master.users import User as UserDBModel
from toxicbuild.output.notifications import Notification
from toxicbuild.ui import settings
from tests import async_test
from tests.functional import (start_master, stop_master, start_webui,
                              stop_webui, start_output, stop_output)


def setUpModule():
    start_master()
    start_webui()
    start_output()


def tearDownModule():
    stop_master()
    stop_webui()
    stop_output()


class RepositoryRestAPITest(TestCase):

    @async_test
    async def setUp(self):
        self.user = UserDBModel(email='a@a.com',
                                allowed_actions=['add_repo', 'add_slave'])
        self.user.set_password('123')
        await self.user.save()
        self.session = requests.session()
        self.slave = SlaveDBModel(name='someslave', host='localhost',
                                  port=1234, use_ssl=False,
                                  owner=self.user, token='some-token')
        await self.slave.save()

        url = settings.LOGIN_URL
        self.session.post(url, data=json.dumps({
            'username_or_email': 'a@a.com',
            'password': '123'}))

    @async_test
    async def tearDown(self):
        await RepoDBModel.drop_collection()
        await UserDBModel.drop_collection()
        await SlaveDBModel.drop_collection()
        self.session.close()

    def test_repo_add(self):
        url = settings.REPO_API_URL
        data = {'name': 'somerepo', 'url': 'https://somebla.com',
                'vcs_type': 'git'}

        self.session.post(url, data=json.dumps(data))

        resp = self.session.get(url)
        repos = resp.json()
        self.assertEqual(len(repos['items']), 1)

    def test_repo_remove(self):
        url = settings.REPO_API_URL
        data = {'name': 'somerepo', 'url': 'https://somebla.com',
                'vcs_type': 'git'}
        self.session.post(url, data=json.dumps(data))
        self.session.delete(url + '?name=a/somerepo')
        resp = self.session.get(url)
        repos = resp.json()
        self.assertEqual(len(repos['items']), 0)

    def test_repo_add_slave(self):
        url = settings.REPO_API_URL
        data = {'name': 'somerepo', 'url': 'https://somebla.com',
                'vcs_type': 'git'}
        self.session.post(url, data=json.dumps(data))
        slave_data = {'name': 'a/someslave'}

        resp = self.session.post(url + 'add-slave?name=a/somerepo',
                                 data=json.dumps(slave_data))
        json_resp = resp.json()
        self.assertEqual(json_resp['repo-add-slave'], 'slave added')

    def test_repo_remove_slave(self):
        url = settings.REPO_API_URL
        data = {'name': 'somerepo', 'url': 'https://somebla.com',
                'vcs_type': 'git'}
        self.session.post(url, data=json.dumps(data))
        slave_data = {'name': 'a/someslave'}

        resp = self.session.post(url + 'add-slave?name=a/somerepo',
                                 data=json.dumps(slave_data))

        resp = self.session.post(url + 'remove-slave?name=a/somerepo',
                                 data=json.dumps(slave_data))

        json_resp = resp.json()
        self.assertEqual(json_resp['repo-remove-slave'], 'slave removed')

    def test_repo_add_branch(self):
        url = settings.REPO_API_URL
        data = {'name': 'somerepo', 'url': 'https://somebla.com',
                'vcs_type': 'git'}
        self.session.post(url, data=json.dumps(data))

        branch_data = {'add_branches': [{'branch_name': 'master',
                                         'notify_only_latest': True}]}
        resp = self.session.post(url + 'add-branch?name=a/somerepo',
                                 data=json.dumps(branch_data))
        self.assertEqual(resp.json()['repo-add-branch'], '1 branches added')

    def test_repo_remove_branch(self):
        url = settings.REPO_API_URL
        data = {'name': 'somerepo', 'url': 'https://somebla.com',
                'vcs_type': 'git'}
        self.session.post(url, data=json.dumps(data))

        branch_data = {'add_branches': [{'branch_name': 'master',
                                         'notify_only_latest': True}]}
        self.session.post(url + 'add-branch?name=a/somerepo',
                          data=json.dumps(branch_data))
        rm_data = {'remove_branches': ['master']}
        resp = self.session.post(url + 'remove-branch?name=a/somerepo',
                                 data=json.dumps(rm_data))

        self.assertEqual(
            resp.json()['repo-remove-branch'], '1 branches removed')


class SlaveRestAPITest(TestCase):

    @async_test
    async def setUp(self):
        self.user = UserDBModel(email='a@a.com',
                                allowed_actions=['add_repo', 'add_slave'])
        self.user.set_password('123')
        await self.user.save()
        self.session = requests.session()

        url = settings.LOGIN_URL
        self.session.post(url, data=json.dumps({
            'username_or_email': 'a@a.com',
            'password': '123'}))

    @async_test
    async def tearDown(self):
        await UserDBModel.drop_collection()
        await SlaveDBModel.drop_collection()
        self.session.close()

    def test_slave_add(self):
        url = settings.SLAVE_API_URL
        data = {'name': 'someslave', 'token': 'asdf', 'host': 'localhost',
                'port': 1234, 'use_ssl': False}
        self.session.post(url, data=json.dumps(data))

        resp = self.session.get(url)
        repos = resp.json()
        self.assertEqual(len(repos['items']), 1)

    def test_repo_remove(self):
        url = settings.REPO_API_URL
        data = {'name': 'someslave', 'token': 'asdf', 'host': 'localhost',
                'port': 1234, 'use_ssl': False}
        self.session.post(url, data=json.dumps(data))
        self.session.delete(url + '?name=someslave')
        resp = self.session.get(url)
        repos = resp.json()
        self.assertEqual(len(repos['items']), 0)


class NotificationRestApiTest(TestCase):

    @async_test
    async def setUp(self):
        # Creating the token for notification api access
        self.real_token = bcrypt_string(
            settings.ACCESS_TOKEN_BASE, bcrypt.gensalt(8))
        self.final_token = base64.b64encode('{}:{}'.format(
            settings.ACCESS_TOKEN_ID,
            settings.ACCESS_TOKEN_BASE).encode()).decode()
        self.token = AccessToken(token_id=settings.ACCESS_TOKEN_ID,
                                 token=self.final_token)
        await self.token.save()

        # login
        self.user = UserDBModel(email='a@a.com',
                                allowed_actions=['add_repo', 'add_slave'])
        self.user.set_password('123')
        await self.user.save()

        self.session = requests.session()

        url = settings.LOGIN_URL
        self.session.post(url, data=json.dumps({
            'username_or_email': 'a@a.com',
            'password': '123'}))

    @async_test
    async def tearDown(self):
        await UserDBModel.drop_collection()
        await AccessToken.drop_collection()
        await Notification.drop_collection()

    def test_enable(self):
        url = settings.NOTIFICATION_API_URL + 'custom-webhook/some-id'
        data = {'webhook_url': 'http://bla.nada'}
        r = self.session.post(url, data=json.dumps(data))
        self.assertTrue(r.status_code, 200)

    def test_disable(self):
        url = settings.NOTIFICATION_API_URL + 'custom-webhook/some-id'

        data = {'webhook_url': 'http://bla.nada'}
        r = self.session.post(url, data=json.dumps(data))
        self.assertTrue(r.status_code, 200)

        r = self.session.delete(url)
        self.assertTrue(r.status_code, 200)
