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

from bson.objectid import ObjectId

from unittest import TestCase
from unittest.mock import patch, MagicMock

from toxicbuild.output.notifications import email

from tests import async_test, AsyncMagicMock


class EmailNotificationTest(TestCase):

    @async_test
    async def setUp(self):
        obj_id = ObjectId()
        self.notification = email.EmailNotification(
            repository_id=obj_id,
            recipients=['a@a.com'])
        self.notification.sender = {'id': 'some-id', 'name': 'some-name'}
        await self.notification.save()

    @patch.object(email.MailSender, 'send', AsyncMagicMock(
        spec=email.MailSender.send))
    @patch.object(email.MailSender, 'connect', AsyncMagicMock(
        spec=email.MailSender.connect))
    @patch.object(email.MailSender, 'disconnect', AsyncMagicMock(
        spec=email.MailSender.disconnect))
    @patch.object(email, 'settings', MagicMock())
    @async_test
    async def test_send_started_message(self):
        buildset_info = {'started': 'here is a datetime string',
                         'commit': '123adf', 'title': 'Some change'}
        await self.notification.send_started_message(buildset_info)
        self.assertTrue(email.MailSender.send.called)

    @patch.object(email.MailSender, 'send', AsyncMagicMock(
        spec=email.MailSender.send))
    @patch.object(email.MailSender, 'connect', AsyncMagicMock(
        spec=email.MailSender.connect))
    @patch.object(email.MailSender, 'disconnect', AsyncMagicMock(
        spec=email.MailSender.disconnect))
    @patch.object(email, 'settings', MagicMock())
    @async_test
    async def test_send_finished_message(self):
        buildset_info = {'finished': 'here is a datetime string',
                         'commit': '123adf', 'title': 'Some change',
                         'status': 'fail', 'total_time': '0:03:01'}
        await self.notification.send_finished_message(buildset_info)
        self.assertTrue(email.MailSender.send.called)
