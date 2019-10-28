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
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch, Mock

from toxicbuild.poller import server

from tests import AsyncMagicMock, async_test


class PollerServerTest(TestCase):

    def setUp(self):
        self.loop = asyncio.get_event_loop()
        self.poller_server = server.PollerServer(self.loop)

    @async_test
    async def test_client_connected_bad_action(self):
        self.poller_server.action = 'bad'

        with self.assertRaises(AssertionError):
            await self.poller_server.client_connected()

    @async_test
    async def test_client_connected(self):
        self.poller_server.action = 'poll'
        self.poller_server.poll_repo = AsyncMagicMock(
            spec=self.poller_server.poll_repo, return_value={'a': 'dict'})
        self.poller_server.send_response = AsyncMagicMock(
            spec=self.poller_server.send_response)

        r = await self.poller_server.client_connected()

        self.assertTrue(r)
        self.assertTrue(self.poller_server.send_response.called)

    @patch.object(server.Poller, 'poll', AsyncMagicMock(
        spec=server.Poller.poll, side_effect=Exception))
    @patch('toxicbuild.poller.poller.settings', Mock(SOURCE_CODE_DIR='.'))
    @patch('toxicbuild.poller.server.PollerServer.log', Mock())
    @async_test
    async def test_poll_repo_exception(self):
        self.poller_server.data = {
            'repo_id': 'some-id',
            'url': 'https://some.where/repo',
            'vcs_type': 'git',
            'since': {'master': datetime.now(),
                      'release': datetime.now()},
            'known_branches': ['master', 'release'],
            'branches_conf': {'master': {'notify_only_latest': True},
                              'release': {'notify_only_latest': True}},
        }

        r = await self.poller_server.poll_repo()

        self.assertTrue(server.Poller.poll.called)
        self.assertEqual(r['clone_status'], 'clone-exception')

    @patch.object(server.Poller, 'poll', AsyncMagicMock(
        spec=server.Poller.poll, return_value=True))
    @patch('toxicbuild.poller.poller.settings', Mock(SOURCE_CODE_DIR='.'))
    @patch('toxicbuild.poller.server.PollerServer.log', Mock())
    @async_test
    async def test_poll_repo(self):
        self.poller_server.data = {
            'repo_id': 'some-id',
            'url': 'https://some.where/repo',
            'vcs_type': 'git',
            'since': {'master': datetime.now(),
                      'release': datetime.now()},
            'known_branches': ['master', 'release'],
            'branches_conf': {'master': {'notify_only_latest': True},
                              'release': {'notify_only_latest': True}},
        }

        r = await self.poller_server.poll_repo()

        self.assertTrue(server.Poller.poll.called)
        self.assertEqual(r['clone_status'], 'ready')

    @patch.object(server.Poller, 'external_poll', AsyncMagicMock(
        spec=server.Poller.external_poll, return_value=True))
    @patch('toxicbuild.poller.poller.settings', Mock(SOURCE_CODE_DIR='.'))
    @patch('toxicbuild.poller.server.PollerServer.log', Mock())
    @async_test
    async def test_external_poll_repo(self):
        self.poller_server.data = {
            'repo_id': 'some-id',
            'url': 'https://some.where/repo',
            'vcs_type': 'git',
            'since': {'master': datetime.now(),
                      'release': datetime.now()},
            'known_branches': ['master', 'release'],
            'branches_conf': {'master': {'notify_only_latest': True},
                              'release': {'notify_only_latest': True}},
            'external': {
                'url': 'https://some.where/external-repo',
                'name': 'some-name',
                'branch': 'master',
                'into': 'master',
            }
        }

        r = await self.poller_server.poll_repo()

        self.assertTrue(server.Poller.external_poll.called)
        self.assertEqual(r['clone_status'], 'ready')
