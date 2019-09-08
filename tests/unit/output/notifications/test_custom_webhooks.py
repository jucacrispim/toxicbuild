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

from toxicbuild.output.notifications import custom_webhook

from tests import async_test, AsyncMagicMock


class CustomWebhookNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        obj_id = ObjectId()
        self.notification = custom_webhook.CustomWebhookNotification(
            webhook_url='https://somwhere.nada',
            repository_id=obj_id)
        await self.notification.save()

    @patch.object(custom_webhook.requests, 'post', AsyncMagicMock(
        spec=custom_webhook.requests.post, return_value=MagicMock()))
    @async_test
    async def test_send_message(self):
        buildset_info = {'repository': {'id': 'some-id', 'name': 'some-name'}}
        await self.notification._send_message(buildset_info)
        self.assertTrue(custom_webhook.requests.post)

    @async_test
    async def test_send_started_message(self):
        self.notification._send_message = AsyncMagicMock(
            spec=self.notification._send_message)
        await self.notification.send_started_message({})
        self.assertTrue(self.notification._send_message.called)

    @async_test
    async def test_send_finished_message(self):
        self.notification._send_message = AsyncMagicMock(
            spec=self.notification._send_message)
        await self.notification.send_finished_message({})
        self.assertTrue(self.notification._send_message.called)
