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
from email.mime.text import MIMEText
import aiosmtplib
from toxicbuild.core.utils import LoggerMixin
from toxicbuild.master import settings


class MailSenderNotConnected(Exception):
    pass


class MailSender(LoggerMixin):
    """Simple mail sender. Takes host/port/auth params from
    settings.

    To send an email, use the context manager:

    .. code-block:: python

       recipients = ['me@mail.com', 'other@mail.com']
       async with MailSender(recipients) as sender:
           await sender.send('Subject', 'This is the message body')

    """

    def __init__(self, recipients):
        self.recipients = recipients
        self.smtp = None
        self.mail_from = settings.SMTP_MAIL_FROM
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.passwd = settings.SMTP_PASSWORD
        self.validate_certs = settings.SMTP_VALIDATE_CERTS
        self.starttls = settings.SMTP_STARTTLS
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
