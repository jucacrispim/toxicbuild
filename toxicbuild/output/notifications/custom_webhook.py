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

from toxicbuild.common.fields import PrettyURLField
from toxicbuild.core import requests

from .base import Notification


class CustomWebhookNotification(Notification):
    """Sends a POST request to a custom URL. The request content type is
    application/json and the body of the request has a json with information
    about a buildset. """

    name = 'custom-webhook'
    pretty_name = 'Custom Webhook'
    description = 'Sends messages to a custom webhook.'

    webhook_url = PrettyURLField(required=True, pretty_name='Webhook URL')

    async def _send_message(self, buildset_info):
        repo = buildset_info['repository']

        self.log('sending message for {} to {}'.format(
            repo['id'], self.webhook_url), level='info')

        headers = {'Content-Type': 'application/json'}
        r = await requests.post(self.webhook_url,
                                json=buildset_info,
                                headers=headers)

        msg = 'response for {} - status: {}'.format(repo['id'], r.status)
        self.log(msg, level='info')

    async def send_started_message(self, buildset_info):
        await self._send_message(buildset_info)

    async def send_finished_message(self, buildset_info):
        await self._send_message(buildset_info)
