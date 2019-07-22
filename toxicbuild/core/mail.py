# -*- coding: utf-8 -*-
# Copyright 2018 Juca Crispim <juca@poraodojuca.net>

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
from email.mime.text import MIMEText
import aiosmtplib
from toxicbuild.core.utils import LoggerMixin


class MailSenderNotConnected(Exception):
    pass


class MailSender(LoggerMixin):
    """Simple mail sender.

    To send an email, use the context manager:

    .. code-block:: python

       recipients = ['me@mail.com', 'other@mail.com']
       smtp_settings = {'host': 'some.host', 'port': 123,
                        'mail_from': 'me@myplace.net',
                        'username': 'me', 'password': '1234',
                        'validate_certs': True, 'starttls': False}

       async with MailSender(recipients, **smtp_settigs) as sender:
           await sender.send('Subject', 'This is the message body')

    """

    def __init__(self, recipients, **smtp_settings):
        self.recipients = recipients
        self.smtp = None
        self.mail_from = smtp_settings['mail_from']
        self.host = smtp_settings['host']
        self.port = smtp_settings['port']
        self.username = smtp_settings['username']
        self.passwd = smtp_settings['password']
        self.validate_certs = smtp_settings.get('validate_certs', True)
        self.starttls = smtp_settings.get('starttls', False)
        self._connected = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc, value, traceback):
        await self.disconnect()

    async def connect(self):
        """Connects to a smtp server."""

        if self._connected:
            msg = 'Already connected to smtp server. Leaving...'
            self.log(msg, level='warning')
            return

        self.smtp = aiosmtplib.SMTP(hostname=self.host, port=self.port,
                                    validate_certs=self.validate_certs)
        if self.starttls:
            await self.smtp.connect(use_tls=False)
            await self.smtp.starttls()
        else:
            await self.smtp.connect()

        await self.smtp.login(self.username, self.passwd)
        self._connected = True

    async def disconnect(self):
        """Closes the connection to the smpt server"""

        await self.smtp.quit()
        self.smtp.close()
        self.smtp = None
        self._connected = False

    async def send(self, subject, message):
        """Send an email message.

        :param subject: Email subject.
        :param message: Email body
        """

        if not self._connected:
            msg = 'You must connect before sending emails'
            raise MailSenderNotConnected(msg)

        msg = MIMEText(message)
        msg['From'] = self.mail_from
        msg['subject'] = subject
        await self.smtp.send_message(msg, recipients=self.recipients)
