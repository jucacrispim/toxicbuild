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

from unittest import TestCase
from unittest.mock import patch, MagicMock

from toxicbuild.core.utils import localtime2utc, datetime2string, now
from toxicbuild.integrations.github import GithubIntegration
from toxicbuild.master.users import User

from toxicbuild.output.notifications import github

from tests import async_test, AsyncMagicMock


class GithubCheckRunNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = User(email='a@a.com')
        await self.user.save()
        self.installation = GithubIntegration(
            github_id=1234, user_id=str(self.user.id),
            user_name=self.user.username)
        await self.installation.save()

        await self.installation.save()
        self.check_run = github.GithubCheckRunNotification(
            installation=self.installation)

    @async_test
    async def tearDown(self):
        await User.drop_collection()
        await GithubIntegration.drop_collection()

    @async_test
    async def test_run(self):
        info = {'status': 'fail', 'id': 'some-id',
                'repository': {'id': 'some-repo-id'}}
        self.check_run._send_message = AsyncMagicMock(
            spec=self.check_run._send_message)

        await self.check_run.run(info)
        self.assertTrue(self.check_run._send_message.called)

    def test_get_payload(self):
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'started': None}
        run_status = 'pending'
        conclusion = None
        expected = {'name': self.check_run.run_name,
                    'head_branch': 'master',
                    'head_sha': '123adf',
                    'status': run_status}
        payload = self.check_run._get_payload(buildset_info, run_status,
                                              conclusion)
        self.assertEqual(payload, expected)

    def test_get_payload_completed(self):
        started = localtime2utc(now())
        finished = localtime2utc(now())
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'started': datetime2string(started),
                         'finished': datetime2string(finished)}

        run_status = 'completed'
        started_at = datetime2string(
            started,
            dtformat="%Y-%m-%dT%H:%M:%S%z").replace('+0000', 'Z')
        completed_at = datetime2string(
            finished,
            dtformat="%Y-%m-%dT%H:%M:%S%z").replace('+0000', 'Z')
        conclusion = None
        expected = {'name': self.check_run.run_name,
                    'head_branch': 'master',
                    'head_sha': '123adf',
                    'started_at': started_at,
                    'status': run_status,
                    'completed_at': completed_at,
                    'conclusion': conclusion}

        payload = self.check_run._get_payload(buildset_info, run_status,
                                              conclusion)
        self.assertEqual(payload, expected)

    @patch.object(github.requests, 'post', AsyncMagicMock(
        spec=github.requests.post))
    @patch.object(GithubIntegration, 'get_header', AsyncMagicMock(
        spec=GithubIntegration.get_header))
    @async_test
    async def test_send_message(self):
        self.check_run.sender = {'id': 'some-id',
                                 'full_name': 'bla/ble',
                                 'external_full_name': 'ble/ble'}
        started = localtime2utc(now())
        finished = localtime2utc(now())
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'started': datetime2string(started),
                         'finished': datetime2string(finished),
                         'id': 'some-id'}

        run_status = 'completed'
        conclusion = None
        ret = MagicMock()
        ret.text = ''
        ret.status = 201
        github.requests.post.return_value = ret

        await self.check_run._send_message(buildset_info, run_status,
                                           conclusion)
        self.assertTrue(github.requests.post.called)
