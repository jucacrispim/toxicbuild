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

from bson.objectid import ObjectId

from toxicbuild.output.notifications import slack

from tests import async_test, AsyncMagicMock


class SlackNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        obj_id = ObjectId()
        sender = {'id': 'some-id',
                  'name': 'some-name'}

        self.notification = slack.SlackNotification(
            repository_id=obj_id, branches=['master', 'other'],
            statuses=['success', 'fail'], webhook_url='https://someurl.nada')
        self.notification.sender = sender
        await self.notification.save()

    @async_test
    async def tearDown(self):
        await slack.Notification.drop_collection()

    @patch.object(slack.requests, 'post', AsyncMagicMock(
        spec=slack.requests.post, return_value=MagicMock()))
    @async_test
    async def test_send_message(self):
        message = {'some': 'thing'}
        await self.notification._send_message(message)
        self.assertTrue(slack.requests.post.called)

    @async_test
    async def test_send_started_message(self):

        buildset_info = {'started': '01/01/1970 00:00:00'}
        self.notification._send_message = AsyncMagicMock(
            self.notification._send_message)
        await self.notification.send_started_message(buildset_info)
        self.assertTrue(self.notification._send_message.called)

    @async_test
    async def test_send_finished_message(self):
        buildset_info = {'finished': '01/01/1970 00:00:00',
                         'status': 'success'}
        self.notification._send_message = AsyncMagicMock(
            self.notification._send_message)
        await self.notification.send_finished_message(buildset_info)
        self.assertTrue(self.notification._send_message.called)
