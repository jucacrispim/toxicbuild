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

import urllib
from mongomotor.fields import ReferenceField

from toxicbuild.integrations.gitlab import GitlabIntegration

from toxicbuild.core import requests
from toxicbuild.output import settings
from .base import Notification


class GitlabCommitStatusNotification(Notification):
    """A plugin that sets a commit status reacting to a buildset that
    was added, started or finished."""

    name = 'gitlab-commit-status'
    """The name of the plugin"""

    events = ['buildset-added', 'buildset-started', 'buildset-finished']
    """Events that trigger the plugin."""

    no_list = True

    installation = ReferenceField(GitlabIntegration)
    """The :class:`~toxicbuild.integrations.gitlab.GitlabIntegration`
    that owns the notification. It is needed because each installation has
    its own auth token and it is needed send the checks.
    """

    async def run(self, buildset_info):
        """Executed when a notification about a build arrives. Reacts
        to buildsets that started or finished.

        :param buildset_info: A dictionary with information about a buildset.
        """

        self.log('Sending notification to gitlab for buildset {}'.format(
            buildset_info['id']), level='info')
        self.log('Info is: {}'.format(buildset_info), level='debug')
        self.sender = buildset_info['repository']
        await self._send_message(buildset_info)

    async def _send_message(self, buildset_info):

        status_tb = {'pending': 'pending',
                     'preparing': 'running',
                     'running': 'running',
                     'success': 'success',
                     'fail': 'failed',
                     'canceled': 'canceled',
                     'exception': 'failed',
                     'warning': 'failed'}

        full_name = urllib.parse.quote(self.sender['external_full_name'],
                                       safe='')
        sha = buildset_info['commit']
        url = settings.GITLAB_API_URL + 'projects/{}/statuses/{}'.format(
            full_name, sha)
        state = status_tb[buildset_info['status']]

        params = {'sha': sha,
                  'ref': buildset_info['branch'],
                  'state': state}
        install = await self.installation
        header = await install.get_headers()

        r = await requests.post(url, headers=header, params=params)

        self.log('response from check for buildset {} - status: {}'.format(
            buildset_info['id'], r.status), level='debug')
        self.log(r.text, level='debug')
