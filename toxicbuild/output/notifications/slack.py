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

from toxicbuild.common.fields import PrettyURLField, PrettyStringField
from toxicbuild.core import requests

from .base import Notification


class SlackNotification(Notification):
    """Plugin that send notifications about builds to slack."""

    name = 'slack-notification'
    pretty_name = "Slack"
    description = "Sends messages to a slack channel"

    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')
    channel_name = PrettyStringField(pretty_name="Channel name")

    def _get_message(self, text):
        return {'text': text, 'channel': self.channel_name,
                'username': 'ToxicBuild'}

    async def _send_message(self, message):
        log_msg = 'sending message for {}'.format(self.sender['id'])
        self.log(log_msg, level='info')

        headers = {'Content-Type': 'application/json'}

        response = await requests.post(self.webhook_url,
                                       json=message,
                                       headers=headers)

        log_msg = 'slack response for {} - status {}'.format(self.sender['id'],
                                                             response.status)
        self.log(log_msg, level='info')
        self.log(response.text, level='debug')

    async def send_started_message(self, buildset_info):

        dt = buildset_info['started']
        build_state = 'Buildset *started* at *{}*'.format(dt)
        title = '[{}] {}'.format(self.sender['name'], build_state)
        msg = self._get_message(title)
        await self._send_message(msg)

    async def send_finished_message(self, buildset_info):

        dt = buildset_info['finished']
        build_state = 'Buildset *finished* at *{}* with status *{}*'.format(
            dt, buildset_info['status'])
        title = '[{}] {}'.format(self.sender['name'], build_state)

        msg = self._get_message(title)
        await self._send_message(msg)
