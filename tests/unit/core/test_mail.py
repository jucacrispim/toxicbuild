# -*- coding: utf-8 -*-
# Copyright 2018, 2023 Juca Crispim <juca@poraodojuca.net>

# This file is part of toxicbuild.

# toxicbuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# toxicbuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.

# You should have received a copy of the GNU Affero General Public License
# along with toxicbuild. If not, see <http://www.gnu.org/licenses/>.

from unittest import TestCase
from unittest.mock import patch, MagicMock, AsyncMock
from toxicbuild.core import mail
from tests import async_test, create_autospec


class MailSenderTest(TestCase):

    def setUp(self):
        self.recipients = ['me@somewhere.com']
        self.smtp_settings = {'mail_from': 'a@a.com', 'host': 'some.host',
                              'port': 123, 'username': 'a@a.com',
                              'password': 'asdf'}
        self.sender = mail.MailSender(self.recipients, **self.smtp_settings)

    @patch.object(mail.MailSender, 'log', MagicMock(spec=mail.MailSender.log))
    @patch.object(mail, 'aiosmtplib', create_autospec(spec=mail.aiosmtplib,
                                                      mock_cls=AsyncMock))
    @async_test
    async def test_connect_already_connected(self):
        self.sender._connected = True
        await self.sender.connect()
        log_level = self.sender.log.call_args[1]['level']
        self.assertEqual('warning', log_level)
        self.assertFalse(mail.aiosmtplib.SMTP.called)

    @patch.object(mail.aiosmtplib.SMTP, 'connect', AsyncMock(
        spec=mail.aiosmtplib.SMTP.connect))
    @patch.object(mail.aiosmtplib.SMTP, 'login', AsyncMock(
        spec=mail.aiosmtplib.SMTP.login))
    @patch.object(mail.aiosmtplib.SMTP, 'starttls', AsyncMock(
        spec=mail.aiosmtplib.SMTP.starttls))
    @async_test
    async def test_connect_starttls(self):
        self.sender.starttls = True
        await self.sender.connect()
        self.assertTrue(self.sender.smtp.connect.called)
        self.assertTrue(self.sender.smtp.starttls.called)
        kw = self.sender.smtp.connect.call_args[1]
        expected_kw = {'use_tls': False}
        self.assertEqual(kw, expected_kw)

    @patch.object(mail.aiosmtplib.SMTP, 'connect', AsyncMock(
        spec=mail.aiosmtplib.SMTP.connect))
    @patch.object(mail.aiosmtplib.SMTP, 'login', AsyncMock(
        spec=mail.aiosmtplib.SMTP.login))
    @patch.object(mail.aiosmtplib.SMTP, 'starttls', AsyncMock(
        spec=mail.aiosmtplib.SMTP.starttls))
    @async_test
    async def test_connect(self):
        self.sender.starttls = False
        await self.sender.connect()
        self.assertTrue(self.sender.smtp.connect.called)
        self.assertFalse(self.sender.smtp.starttls.called)
        kw = self.sender.smtp.connect.call_args[1]
        expected_kw = {}
        self.assertEqual(kw, expected_kw)

    @async_test
    async def test_disconnect(self):
        m_quit = AsyncMock()
        m_close = MagicMock()

        self.sender.smtp = MagicMock()
        self.sender.smtp.quit = m_quit
        self.sender.smtp.close = m_close()
        await self.sender.disconnect()
        self.assertTrue(m_quit.called)
        self.assertTrue(m_close.called)
        self.assertFalse(self.sender._connected)

    @async_test
    async def test_send_not_connected(self):
        with self.assertRaises(mail.MailSenderNotConnected):
            await self.sender.send('subject', 'body')

    @async_test
    async def test_send(self):
        self.sender.smtp = MagicMock()
        m_send_message = AsyncMock()
        self.sender.smtp.send_message = m_send_message
        self.sender._connected = True
        await self.sender.send('subject', 'body')
        self.assertTrue(m_send_message.called)
