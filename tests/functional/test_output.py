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

import asyncio
import json
from unittest import TestCase
from pyrocumulus.auth import AccessToken, Permission
from toxicbuild.core import requests
from toxicbuild.master.repository import Repository
from toxicbuild.master.slave import Slave
from toxicbuild.master.users import User
from toxicbuild.output import create_auth_token
from toxicbuild.output.notifications import Notification
from toxicbuild.output import settings
from tests import async_test
from tests.functional import (start_master, stop_master, start_slave,
                              stop_slave, start_output, stop_output,
                              DummyMasterHoleClient, start_customwebserver,
                              stop_customwebserver, start_poller, stop_poller,
                              start_scheduler, stop_scheduler)
from tests.functional.custom_webhook import WebHookMessage


class DummyUIClient(DummyMasterHoleClient):

    async def create_slave(self):
        slave_port = settings.SLAVE_PORT
        r = await super().create_slave(slave_port)
        return r


def setUpModule():
    start_slave()
    start_scheduler()
    start_poller()
    start_master()
    start_output()
    start_customwebserver()


def tearDownModule():
    stop_output()
    stop_master()
    stop_scheduler()
    stop_poller()
    stop_slave()
    stop_customwebserver()


class NotificationTest(TestCase):

    @classmethod
    @async_test
    async def setUpClass(cls):
        cls.user = User(email='toxic@a.com', is_superuser=True)
        await cls.user.save()
        cls.auth_token = await cls._create_access_token()
        dc = DummyUIClient(cls.user, settings.HOLE_ADDR,
                           settings.HOLE_PORT)

        async with dc:
            await dc.create_slave()

        async with dc:
            cls.repo_info = await dc.create_repo()

        async with dc:
            await dc.wait_build_complete()

    @classmethod
    @async_test
    async def tearDownClass(cls):
        await Slave.drop_collection()
        await Repository.drop_collection()
        await User.drop_collection()
        await AccessToken.drop_collection()
        await Permission.drop_collection()

    @async_test
    async def tearDown(self):
        await Notification.drop_collection()
        await WebHookMessage.drop_collection()

    @classmethod
    async def _create_access_token(cls):
        uncrypted_token = await create_auth_token()
        return uncrypted_token

    @async_test
    async def test_add_notification(self):
        notif_name = 'custom-webhook'
        kw = {'webhook_url': 'http://localhost:8123/webhookmessage/',
              'repository_id': str(self.repo_info['id'])}
        url = 'http://localhost:9234/{}'.format(notif_name)
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        r = await requests.post(url, data=json.dumps(kw),
                                headers=headers)
        self.assertEqual(r.status, 200)

    @async_test
    async def test_trigger_notification(self):

        notif_name = 'custom-webhook'
        kw = {'webhook_url': 'http://localhost:8123/webhookmessage/',
              'repository_id': str(self.repo_info['id'])}
        url = 'http://localhost:9234/{}'.format(notif_name)
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        await requests.post(url, data=json.dumps(kw), headers=headers)

        dc = DummyUIClient(self.user, settings.HOLE_ADDR,
                           settings.HOLE_PORT)
        async with dc:
            await dc.start_build()

        async with dc:
            await dc.wait_build_complete()

        timeout = 10
        t = 0
        while t < timeout:
            count = await WebHookMessage.objects.count()
            try:
                self.assertEqual(count, 3)
            except:
                pass

            else:
                break

            await asyncio.sleep(0.1)
            t += 1

        self.assertEqual(count, 3)

    @async_test
    async def test_remove_notification(self):
        notif_name = 'custom-webhook'
        kw = {'webhook_url': 'http://localhost:8123/webhookmessage/',
              'repository_id': str(self.repo_info['id'])}
        url = 'http://localhost:9234/{}'.format(notif_name)
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        await requests.post(url, data=json.dumps(kw),
                            headers=headers)

        kw = {'repository_id': str(self.repo_info['id'])}
        url = 'http://localhost:9234/{}'.format(notif_name)
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        r = await requests.delete(url, data=json.dumps(kw),
                                  headers=headers)

        self.assertEqual(r.status, 200)

    @async_test
    async def test_list_notifications(self):
        url = 'http://localhost:9234/list/'
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        r = await requests.get(url, headers=headers)
        r = r.json()

        self.assertEqual(len(r['notifications']), 3)

    @async_test
    async def test_list_notifications_for_repo(self):

        notif_name = 'custom-webhook'
        kw = {'webhook_url': 'http://localhost:8123/webhookmessage/',
              'repository_id': str(self.repo_info['id'])}
        url = 'http://localhost:9234/{}'.format(notif_name)
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        await requests.post(url, data=json.dumps(kw), headers=headers)

        url = 'http://localhost:9234/list/{}'.format(self.repo_info['id'])
        headers = {'Authorization': 'token: {}'.format(self.auth_token)}
        r = await requests.get(url, headers=headers)
        notifications = r.json()['notifications']

        for n in notifications:
            if n['name'] == 'custom-webhook':
                break

        self.assertEqual(n['webhook_url']['value'],
                         'http://localhost:8123/webhookmessage/')
