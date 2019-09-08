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

from toxicbuild.integrations.gitlab import GitlabIntegration
from toxicbuild.master.users import User
from toxicbuild.output.notifications import gitlab

from tests import async_test, AsyncMagicMock


class GitlabCommitStatusNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        self.user = User(email='a@a.com')
        await self.user.save()
        self.installation = GitlabIntegration(
            external_user_id=1234, user_id=str(self.user.id),
            user_name=self.user.username)
        await self.installation.save()

        await self.installation.save()
        self.notif = gitlab.GitlabCommitStatusNotification(
            installation=self.installation)

    @async_test
    async def tearDown(self):
        await User.drop_collection()
        await GitlabIntegration.drop_collection()

    @async_test
    async def test_run(self):
        info = {'status': 'fail', 'id': 'some-id',
                'repository': {'id': 'some-repo-id'}}
        self.notif._send_message = AsyncMagicMock(
            spec=self.notif._send_message)

        await self.notif.run(info)
        self.assertTrue(self.notif._send_message.called)

    @patch.object(GitlabIntegration, 'get_headers', AsyncMagicMock(
        spec=GitlabIntegration.get_headers))
    @patch.object(gitlab.requests, 'post', AsyncMagicMock(
        spec=gitlab.requests.post))
    @async_test
    async def test_send_message(self):
        self.notif.sender = {'id': 'some-id',
                             'full_name': 'bla/ble',
                             'external_full_name': 'ble/ble'}
        buildset_info = {'branch': 'master', 'commit': '123adf',
                         'status': 'exception',
                         'id': 'some-id'}

        ret = MagicMock()
        ret.text = ''
        ret.status = 201
        gitlab.requests.post.return_value = ret

        await self.notif._send_message(buildset_info)
        self.assertTrue(gitlab.requests.post.called)
