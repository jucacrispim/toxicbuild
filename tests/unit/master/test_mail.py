# -*- coding: utf-8 -*-

# Copyright 2017 Juca Crispim <juca@poraodojuca.net>

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
from unittest import TestCase
from unittest.mock import MagicMock, patch
from toxicbuild.master import mail
from tests import async_test, AsyncMagicMock

mock_settings = MagicMock()
mock_settings.SMTP_MAIL_FROM = 'tester@somewhere.net'
mock_settings.SMTP_HOST = 'localhost'
mock_settings.SMTP_PORT = 587
mock_settings.SMTP_USERNAME = 'tester'
mock_settings.SMTP_PASSWORD = '123'
mock_settings.SMTP_VALIDATE_CERTS = True
mock_settings.SMTP_STARTTLS = True

no_starttls_mock_settings = MagicMock()
no_starttls_mock_settings.SMTP_MAIL_FROM = 'tester@somewhere.net'
no_starttls_mock_settings.SMTP_HOST = 'localhost'
no_starttls_mock_settings.SMTP_PORT = 587
no_starttls_mock_settings.SMTP_USERNAME = 'tester'
no_starttls_mock_settings.SMTP_PASSWORD = '123'
no_starttls_mock_settings.SMTP_VALIDATE_CERTS = True
no_starttls_mock_settings.SMTP_STARTTLS = False


class MailSenderTest(TestCase):

    @patch.object(mail, 'settings', mock_settings)
    @patch.object(mail, 'aiosmtplib', MagicMock())
    def setUp(self):
        self.recipients = ['me@somewhere.com']
        self.sender = mail.MailSender(self.recipients)

    @patch.object(mail.MailSender, 'log', MagicMock())
    @patch.object(mail, 'aiosmtplib', MagicMock())
    @async_test
    async def test_connect_already_connected(self):
        self.sender._connected = True
        await self.sender.connect()
        log_msg = self.sender.log.call_args[0][0]
        self.assertIn('Already connected', log_msg)
        self.assertFalse(mail.aiosmtplib.SMTP.called)

    @patch.object(mail, 'aiosmtplib', MagicMock())
    @async_test
    async def test_connect_starttls(self):
        mail.aiosmtplib.SMTP.return_value.connect = AsyncMagicMock()
        mail.aiosmtplib.SMTP.return_value.starttls = AsyncMagicMock()
        mail.aiosmtplib.SMTP.return_value.login = AsyncMagicMock()
        await self.sender.connect()
        self.assertTrue(self.sender.smtp.connect.called)
        self.assertTrue(self.sender.smtp.starttls.called)
        kw = self.sender.smtp.connect.call_args[1]
        expected_kw = {'use_tls': False}
        self.assertEqual(kw, expected_kw)

    @patch.object(mail, 'aiosmtplib', MagicMock())
    @patch.object(mail, 'settings', no_starttls_mock_settings)
    @async_test
    async def test_connect(self):
        self.sender = mail.MailSender(self.recipients)
        mail.aiosmtplib.SMTP.return_value.connect = AsyncMagicMock()
        mail.aiosmtplib.SMTP.return_value.starttls = AsyncMagicMock()
        mail.aiosmtplib.SMTP.return_value.login = AsyncMagicMock()
        await self.sender.connect()
        self.assertTrue(self.sender.smtp.connect.called)
        self.assertFalse(self.sender.smtp.starttls.called)
        kw = self.sender.smtp.connect.call_args[1]
        expected_kw = {}
        self.assertEqual(kw, expected_kw)

    @async_test
    async def test_disconnect(self):
        m_quit = AsyncMagicMock()
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
        m_send_message = AsyncMagicMock()
        self.sender.smtp.send_message = m_send_message
        self.sender._connected = True
        await self.sender.send('subject', 'body')
        self.assertTrue(m_send_message.called)
