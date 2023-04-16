# -*- coding: utf-8 -*-
# Copyright 2019 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

import asyncio
from copy import copy
from unittest import TestCase

from toxicbuild.core.client import BaseToxicClient
from toxicbuild.common import common_setup

from tests import async_test

from . import REPO_DIR, OTHER_REPO_DIR, start_new_poller, stop_new_poller


def setUpModule():
    from toxicbuild.poller import settings
    loop = asyncio.get_event_loop()
    start_new_poller()
    loop.run_until_complete(common_setup(settings))


def tearDownModule():
    stop_new_poller()


class DummyPollerClient(BaseToxicClient):

    def __init__(self, *args, **kwargs):
        kwargs['use_ssl'] = True
        kwargs['validate_cert'] = False
        super().__init__(*args, **kwargs)
        self.body = {
            'repo_id': 'some-id',
            'url': REPO_DIR,
            'vcs_type': 'git',
            'since': None,
            'known_branches': [],
            'branches_conf': {},
        }
        self.external_body = copy(self.body)
        self.external_body['external'] = {
            'url': OTHER_REPO_DIR,
            'name': 'other-repo',
            'branch': 'master',
            'into': 'other-repo/master',
        }

    async def request2server(self, action, body):

        data = {'action': action, 'body': body,
                'token': '123'}
        await self.write(data)
        response = await self.get_response()
        return response['body'][action]

    async def poll(self):
        action = 'poll'
        r = await self.request2server(action, self.body)
        return r

    async def poll_external(self):
        action = 'poll'
        r = await self.request2server(action, self.external_body)
        return r


class PollerTest(TestCase):

    @async_test
    async def setUp(self):
        self.client = DummyPollerClient('localhost', 9911)
        await self.client.connect()

    @async_test
    async def tearDown(self):
        self.client.disconnect()

    @async_test
    async def test_poll(self):
        r = await self.client.poll()
        self.assertTrue(r['revisions'])
        self.assertTrue(r['revisions'][0]['config'])

    @async_test
    async def test_poll_external(self):
        r = await self.client.poll_external()

        self.assertEqual(len(r['revisions']), 1)
        self.assertTrue(r['revisions'][0]['config'])
