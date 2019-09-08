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

from mongomotor.fields import StringField

from toxicbuild.common.fields import PrettyListField
from toxicbuild.core.mail import MailSender as MailSenderCore

from toxicbuild.output import settings

from .base import Notification


class MailSender(MailSenderCore):
    """Mail sender that take its configurations from the settings file"""

    def __init__(self, recipients):
        smtp_settings = {'host': settings.SMTP_HOST,
                         'port': settings.SMTP_PORT,
                         'mail_from': settings.SMTP_MAIL_FROM,
                         'username': settings.SMTP_USERNAME,
                         'password': settings.SMTP_PASSWORD,
                         'validate_certs': settings.SMTP_VALIDATE_CERTS,
                         'starttls': settings.SMTP_STARTTLS}
        super().__init__(recipients, **smtp_settings)


async def send_email(recipients, subject, message):

    async with MailSender(recipients) as sender:
        await sender.send(subject, message)

    return True


class EmailNotification(Notification):
    """Sends notification about buildsets through email"""

    name = 'email-notification'
    pretty_name = 'Email'
    description = 'Sends email messages'

    recipients = PrettyListField(StringField(), pretty_name="Recipients",
                                 required=True)

    async def send_started_message(self, buildset_info):
        started = buildset_info['started']
        repo_name = self.sender['name']
        subject = '[ToxicBuild][{}] Build started at {}'.format(
            repo_name, started)
        message = 'A build has just started for the repository {}.'.format(
            repo_name)

        message += '\n\ncommit: {}\ntitle: {}'.format(buildset_info['commit'],
                                                      buildset_info['title'])

        await send_email(self.recipients, subject, message)

    async def send_finished_message(self, buildset_info):
        dt = buildset_info['finished']
        repo_name = self.sender['name']
        subject = '[ToxicBuild][{}] Build finished at {}'.format(repo_name, dt)
        message = 'A build finished for the repository {}'.format(repo_name)
        message += '\n\ncommit: {}\ntitle: {}'.format(buildset_info['commit'],
                                                      buildset_info['title'])
        message += '\ntotal time: {}\nstatus: {}'.format(
            buildset_info['total_time'], buildset_info['status'])

        await send_email(self.recipients, subject, message)
